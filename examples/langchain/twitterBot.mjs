import dotenv from 'dotenv';
dotenv.config();
import needle from 'needle';
import { TwitterApi } from 'twitter-api-v2';
import mongoose from 'mongoose';

const FASTAPI_ENDPOINT = 'https://myseelia.life/twitterQuery';
const BEARER_TOKEN = process.env.BEARER_TOKEN;
const postTweetEndpointUrl = "https://api.twitter.com/2/tweets";

// Your keys and tokens from the .env file
const consumerKey = process.env.API_KEY;
const consumerSecret = process.env.API_SECRET;
const accessToken = process.env.ACCESS_TOKEN;
const accessSecret = process.env.ACCESS_SECRET;

// Initialize the Twitter client
const twitterClient = new TwitterApi({
    appKey: consumerKey,
    appSecret: consumerSecret,
    accessToken: accessToken,
    accessSecret: accessSecret,
});

// Ready to make calls on behalf of the user
const rwClient = twitterClient.readWrite;

// Mongodb for indexing tweets
mongoose.connect('mongodb://localhost/twitterBotDb', {
    useNewUrlParser: true,
    useUnifiedTopology: true,
});

const tweetSchema = new mongoose.Schema({
    tweetId: { type: String, required: true, unique: true },
    tweetText: String,
    repliedTo: { type: Boolean, default: false },
    replyText: String,
    createdAt: { type: Date, default: Date.now }, 
    fullResponse: String,
});

const Tweet = mongoose.model('Tweet', tweetSchema);

mongoose.connection.on('error', console.error.bind(console, 'MongoDB connection error:'));

// Base URL for full answers
const baseURL = 'https://myseelia.life/tweet/';

// Function to post a tweet
async function postTweet(replyText, fullResponseContent, inReplyToTweetId) {
    if (typeof replyText !== 'string' || replyText.trim().length === 0) {
        console.error('Error posting reply: replyText is undefined or empty');
        return; // Exit early
    }
    
    // Generate the URL for the full answer
    const fullAnswerURL = `${baseURL}${inReplyToTweetId}`;
    console.log('Full Answer URL:', fullAnswerURL);
    // Calculate remaining characters after adding the URL
    const maxReplyLength = 280 - (fullAnswerURL.length + " Full Answer: ".length);

    // Shorten the reply text if necessary
    if (replyText.length > maxReplyLength) {
        replyText = replyText.substring(0, maxReplyLength - 3) + "...";
    }

    // Append the URL for the full answer
    replyText += ` Full Answer: ${fullAnswerURL}`;

    try {
        const response = await rwClient.v2.reply(replyText, inReplyToTweetId);
        console.log('Reply posted:', response.data);

        // Upsert the tweet and reply in MongoDB
        await Tweet.findOneAndUpdate({ tweetId: inReplyToTweetId }, {
            tweetId: inReplyToTweetId,
            replyText: replyText, // Include the full reply text with URL
            repliedTo: true,
            fullResponse: fullResponseContent,
        }, { upsert: true, new: true });

        return response.data;
    } catch (error) {
        console.error('Error posting reply:', error);
    }
}

async function sendQuestionToBackend(question, username) {
    try {
        const response = await fetch(FASTAPI_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question, history: [], username }),
        });

        if (!response.ok) {
            console.error("Error with the backend API request:", response.statusText);
            return "There was an error processing your request."; // Return a default error message
        }

        // Ensure the response is JSON before attempting to parse
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            console.error('Failed to fetch JSON, received:', await response.text());
            return "There was an error processing your request."; // Return a default error message
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Failed to send question to backend:`, error);
        return "There was an error processing your request."; // Return a default error message on catch
    }
}

// Function to search tweets and post a reply to each found tweet
async function searchAndReply() {
    const searchEndpointUrl = "https://api.twitter.com/2/tweets/search/recent";
    const params = {
        'query': '"/ask @ReFiChat" -is:retweet',
        'tweet.fields': 'author_id,created_at',
        'max_results': 10 // Adjust based on your rate limits and needs
    };

    try {
        const res = await needle('get', searchEndpointUrl, params, {
            headers: {
                "authorization": `Bearer ${BEARER_TOKEN}`,
                "User-Agent": "v2RecentSearchJS",
            }
        });

        if (res.body && res.body.data && res.body.data.length > 0) {
            for (const tweet of res.body.data) {
                // Strip off the "/ask @ReFiChat" prefix from the tweet text
                const strippedTweetText = tweet.text.replace(/\/ask @refichat[ ,]?/i, "");
                console.log("strippedTweetText: ", strippedTweetText)
                const existingTweet = await Tweet.findOne({ tweetId: tweet.id });
                if (!existingTweet) {
                    // Save tweet as "seen" to prevent processing it again, using the modified tweet text
                    const newTweet = new Tweet({
                        tweetId: tweet.id,
                        tweetText: strippedTweetText, // Use the stripped tweet text here
                        repliedTo: false, // Initially false, to be updated upon replying
                    });
                    await newTweet.save();

                    if (postCount < postLimit) {
                        // Send the modified tweet text to the backend for processing
                        const response = await sendQuestionToBackend(strippedTweetText, `@${tweet.author_id}`);
                        if (response.result && response.result.final_response_twitter !== "There was an error processing your request.") {
                            let fullResponseContent = response.result.final_response;

                            // Check if fullResponseContent is an object, if so, stringify it
                            if (typeof fullResponseContent === 'object') {
                                fullResponseContent = JSON.stringify(fullResponseContent);
                            }

                            console.log("fullResponseContent in searchAndReply: ", fullResponseContent);

                            await postTweet(response.result.final_response_twitter, fullResponseContent, tweet.id);

                            console.log('Tweet replied to with backend answer:', tweet.id);
                        } else {
                            console.log('Error or undefined response from backend:', response);
                        }
                    } else {
                        console.log('Post limit reached, tweet logged without replying:', tweet.id);
                    }
                }
            }
        } else {
            console.log('No new tweets found or unsuccessful request to search tweets');
        }
    } catch (error) {
        console.error('Error during search and reply:', error);
    }
}

let postCount = 0;
const postLimit = 100; // Maximum number of posts allowed in 24 hours
const resetPostCountEpoch = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

// Reset the post count every 24 hours
setInterval(async () => {
    console.log('Resetting post count and checking for unreplied tweets.');
    postCount = 0; // Reset the post count for the new day

    // Attempt to reply to new tweets first
    try {
        await searchAndReply();
    } catch (error) {
        console.error('Error during search and reply:', error);
    }

    // Then, find the most recent tweets from previous epochs that haven't been replied to yet
    try {
        const unrepliedTweets = await Tweet.find({ repliedTo: false }).sort({ createdAt: -1 }).limit(postLimit);

        for (const tweet of unrepliedTweets) {
            if (postCount >= postLimit) break; // Safeguard to ensure we don't exceed the limit

            const replyText = "@ReFiChat Here's a test reply!";
            await postTweet(replyText, tweet.tweetId);
            postCount++;
            tweet.repliedTo = true;
            tweet.replyText = replyText;
            await tweet.save();
            console.log('Catch-up reply posted:', tweet.tweetId);
        }
    } catch (error) {
        console.error('Error processing unreplied tweets:', error);
    }
}, resetPostCountEpoch);

// Schedule to check for mentions without exceeding search limit
const searchInterval = 15 * 60 * 1000 / 60; // Distribute 60 searches evenly over 15 minutes
setInterval(() => {
    if (postCount < postLimit) {
        searchAndReply().catch(console.error);
    }
}, searchInterval);
