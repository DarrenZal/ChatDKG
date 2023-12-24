from fastapi import FastAPI, HTTPException  # Add HTTPException here
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import RAG_SPARQL 
import createSPARQL
from pprint import pprint

app = FastAPI()

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Define a Pydantic model for the request data
class QueryRequest(BaseModel):
    question: str
    history: list[dict[str, str]]  # Add this line

@app.post("/query")
async def query(query_request: QueryRequest):
    try:
        question = query_request.question
        history = query_request.history  # Extract history from the request
        result = await RAG_SPARQL.RAGandSPARQL(question, history)  # Pass history to the function
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/EntityMatchAnswer")
async def EntityMatchAnswer(query_request: QueryRequest):
    try:
        question = query_request.question
        matched_entities, response = createSPARQL.EntityMatchAnswer(question)
        print("Generated EntityMatches: ")
        pprint(matched_entities)
        return {"matched_entities": matched_entities, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))