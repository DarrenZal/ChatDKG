from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pprint import pprint
import RAG_SPARQL
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

        result = await RAG_SPARQL.RAGandSPARQL(question, history)

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