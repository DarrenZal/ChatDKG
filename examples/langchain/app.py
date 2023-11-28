from fastapi import FastAPI, HTTPException  # Add HTTPException here
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import createSPARQL 

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

@app.post("/generate_query")
async def generate_query(query_request: QueryRequest):
    try:
        question = query_request.question
        sparql_query = createSPARQL.generate_sparql_query(question)
        print("Generated SPARQL query:", sparql_query)
        return {"sparql_query": sparql_query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/EntityMatchAnswer")
async def EntityMatchAnswer(query_request: QueryRequest):
    try:
        question = query_request.question
        matched_entities, response = createSPARQL.EntityMatchAnswer(question)
        print("Generated EntityMatches", matched_entities)
        print("Generated EntityMatchText:", response)
        return {"matched_entities": matched_entities, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))