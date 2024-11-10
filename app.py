from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pprint import pprint
import RAG_SPARQL_MAINNET
from twitter_processing_mainnet import process_query_for_twitter
from tweet_Info import find_tweet_by_id
import logging
from logging.handlers import RotatingFileHandler

app = FastAPI()

# Configure file logging
log_file = "query_logs.log"
logging.basicConfig(level=logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=1000000, backupCount=5)
logger = logging.getLogger("uvicorn.error")
logger.addHandler(handler)


# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Set up logging
logger = logging.getLogger("uvicorn.error")

# Define a Pydantic model for the request data
class QueryRequest(BaseModel):
    question: str
    history: list
    username: str

class FeedbackRequest(BaseModel):
    username: str
    feedback: str

@app.post("/query")
async def query(query_request: QueryRequest):
    try:
        question = query_request.question
        history = query_request.history
        username = query_request.username  # Get the username from the request

        result = await RAG_SPARQL_MAINNET.RAGandSPARQL(question, history)

        # Log the query, result, and username
        with open(log_file, 'a') as file:
            file.write(f"User: {username}, Question: {question}, Result: {result}\n")

        return {"result": result}
    except Exception as e:
        logger.error(f"Internal Server Error: {str(e)} for user {username}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/feedback")
async def feedback(feedback_request: FeedbackRequest):
    try:
        username = feedback_request.username
        feedback = feedback_request.feedback

        # Log the feedback
        with open(log_file, 'a') as file:
            file.write(f"User: {username}, Feedback: {feedback}\n")

        return {"message": "Feedback received"}
    except Exception as e:
        logger.error(f"Error receiving feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
# Define a Pydantic model for the Twitter query request data
class TwitterQueryRequest(BaseModel):
    question: str
    username: str
    history: list = []  # Assuming you might want to pass a conversation history or similar

@app.post("/twitterQuery")
async def twitter_query(twitter_query_request: TwitterQueryRequest):
    try:
        question = twitter_query_request.question
        history = twitter_query_request.history
        username = twitter_query_request.username  # This now correctly captures the username

        response = await process_query_for_twitter(question, history)

        print("response in app.py from process_query_for_twitter ")
        print(response)

        # Log the query, result, and username
        with open(log_file, 'a') as file:
            file.write(f"User: {username}, Question: {question}, Result: {response}\n")

        return {"result": response}
    except Exception as e:
        logger.error(f"Internal Server Error: {str(e)} for Twitter user  {username}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/api/tweet/{tweet_id}")
def get_tweet(tweet_id: str):
    logger.info(f"Fetching tweet for ID: {tweet_id}")
    try:
        tweet_info = find_tweet_by_id(tweet_id)
        if tweet_info:
            # Use .dict() to convert Pydantic model to dict for JSON response
            return tweet_info.dict(by_alias=True)  # `by_alias=True` to use field aliases like '_id' -> 'id'
        else:
            raise HTTPException(status_code=404, detail="Tweet not found")
    except Exception as e:
        logger.error(f"Error fetching tweet: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))