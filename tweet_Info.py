from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from datetime import datetime

def to_string(v):
    if isinstance(v, ObjectId):
        return str(v)
    raise TypeError("Input is not an instance of ObjectId")

class TweetModel(BaseModel):
    tweetId: str
    tweetText: Optional[str] = None
    repliedTo: bool
    replyText: Optional[str] = None
    createdAt: datetime
    fullResponse: Optional[str] = None 

    class Config:
        orm_mode = True

# Initialize MongoDB client and select database
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['twitterBotDb']
tweets_collection = db['tweets']

def find_tweet_by_id(tweet_id: str):
    tweet_info = tweets_collection.find_one({'tweetId': tweet_id})
    print("tweet_info: ")
    print(tweet_info)
    if tweet_info:
        tweet_info.pop('_id', None)  # Remove '_id' if it exists in the document
        tweet_info['fullResponse'] = tweet_info.get('fullResponse', 'No full response available.')
        return TweetModel(**tweet_info)
    return None