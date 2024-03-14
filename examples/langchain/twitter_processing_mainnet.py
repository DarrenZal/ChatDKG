import time
start_time = time.time()
import os
import json
import asyncio
import concurrent.futures
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pymilvus import MilvusClient
from pprint import pprint
from dkg import DKG
from dkg.providers import BlockchainProvider, NodeHTTPProvider
print(f"importing libraries took {time.time() - start_time:.2f} seconds.")
start_time = time.time()

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

def timed_function(func):
    """Decorator to measure execution time of a function."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time:.2f} seconds.")
        return result
    return wrapper

# Milvus Client Initialization
CLUSTER_ENDPOINT = os.getenv("MILVUS_URI_MAINNET")
TOKEN = os.getenv("MILVUS_TOKEN_MAINNET")
milvus_client = MilvusClient(uri=CLUSTER_ENDPOINT, token=TOKEN)

# Initialize the Sentence Transformer model
MODEL_NAME = 'sentence-transformers/multi-qa-MiniLM-L6-cos-v1'
sentence_model = SentenceTransformer(MODEL_NAME)

# Function to convert a list of strings to embeddings
def convert_to_embeddings(strings):
    return sentence_model.encode(strings, convert_to_tensor=True).numpy().tolist()

@timed_function
def prepend_ontology_prefixes(query, ontology_content):
    # Extracting prefixes from the ontology content
    prefixes = extract_prefixes(ontology_content)

    # Prepending extracted prefixes to the query
    amended_query = prefixes + "\n" + query
    return amended_query

@timed_function
def extract_prefixes(ontology_content):
    # Extract prefixes like '@prefix schema: <http://schema.org/> .'
    lines = ontology_content.split("\n")
    prefix_lines = [line for line in lines if line.startswith("@prefix")]
    sparl_prefixes = []

    for line in prefix_lines:
        # Remove the '.' at the end and split
        parts = line.rstrip('.').split()
        if len(parts) >= 3:
            # Convert '@prefix' to 'PREFIX'
            prefix = parts[1]
            uri = parts[2]
            sparl_prefix = f"PREFIX {prefix} {uri}"
            sparl_prefixes.append(sparl_prefix)

    return "\n".join(sparl_prefixes)


def read_ontology_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content


def execute_sparql_query(query):
    try:
        # Initialize DKG
        ot_node_hostname = os.getenv("OT_NODE_HOSTNAME_MAINNET")+":8900"
        node_provider = NodeHTTPProvider(ot_node_hostname)
        blockchain_provider = BlockchainProvider(
            os.getenv("RPC_ENDPOINT_MAINNET"), 
            os.getenv("WALLET_PRIVATE_KEY_MAINNET")
        )

        # Initialize the DKG client
        dkg = DKG(node_provider, blockchain_provider)

        # Execute the query
        query_graph_result = dkg.graph.query(query, repository="privateCurrent")
        print("query_graph_result: ", query_graph_result)

        if query_graph_result:
            return query_graph_result
        else:
            return []

    except Exception as e:
        print(f"Error during SPARQL query execution: {e}")
        return []



@timed_function
def extract_entities_and_classify(question: str, query_matches, entity_matches, ontology_content, history) -> Dict[str, Any]:
    try:
        # Initialize variables
        query = ''  # Initialize query as an empty string
        response = ''  # Initialize response as an empty string
        UALs = []  # Initialize UALs as an empty list

        # Format query and entity matches for the prompt
        formatted_query_matches = ", ".join([f"Query Match: {match}" for match in query_matches])
        formatted_entity_matches = ", ".join([f"Entity Match: {match}" for match in entity_matches])
        pprint("formatted_entity_matches: ")
        pprint(formatted_entity_matches)

        # Call the OpenAI ChatCompletion API
        completion = client.chat.completions.create(
            model="gpt-4-0125-preview",
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "This is for a ReFi chatbot to answer questions about Regenerative Finance (ReFi). "
                        "Upon receiving a prompt, always generate a response using Retrieval Augmented Generation (RAG), "
                        "and also generate a SPARQL query if the prompt can be answered using the provided OWL ontology. "
                        "For RAG, Ignore any of the Entity Matches that are irrelevant to the prompt. Also, Format the response with HTML line breaks (<br>) for use in HTML."
                        "RAG responses should summarize relevant information and, if applicable, include unique UALs of entity matches used. "
                        "SPARQL queries should aggregate total values before filters and include details for clarity. "
                        "Retrieve all attributes for a subject in question when possible, ie retrieve more info than necessary"
                        "Consider the included SPARQL query matches 'Query Matches' from the database when creating the query. "
                        "Even if classified as SPARQL, always try to generate RAG response as well if you can."
                        "Always format responses in JSON, with 'Classification' indicating 'RAG' or 'SPARQL', and include both responses when SPARQL is applicable. "
                        "Ensure RAG responses are formatted with HTML line breaks for display in HTML environments. "
                        "Example output structure for RAG: {'Classification': 'RAG', 'Response': 'Text here <br><br> Additional text.', 'UALs': ['did:example']}. "
                        "For SPARQL: {'Classification': 'SPARQL', 'SPARQL': 'SELECT ?entity WHERE {...}'}."
                    )
                },
                {
                    "role": "user",
                    "content": f"prompt: '{question}', Query Matches: '{formatted_query_matches}', Entity Matches: '{formatted_entity_matches}', Ontology: '{ontology_content}'"
                },
                *history  # Include chat history in the API call
            ]
        )

        # Log token usage for cost estimation
        completion_tokens = completion.usage.completion_tokens
        prompt_tokens = completion.usage.prompt_tokens
        OpenAICallCost = 0.01 * prompt_tokens / 1000 + 0.03 * completion_tokens / 1000
        print(f"extract_entities_and_classify.  input tokens: {prompt_tokens}, output tokens: {completion_tokens}, cost: {OpenAICallCost}")

        # Processing API response
        extracted_content = completion.choices[0].message.content
        print("Extracted Content:", extracted_content)  # For debugging
        data = json.loads(extracted_content)

        classification = data.get("Classification", "Error")
        if classification != "Error":
            if classification == "SPARQL":
                query = data.get("SPARQL", '')
            response = data.get("Response", "")
            UALs = data.get("UALs", [])

            # Remove duplicates by converting the list to a set, then back to a list
            unique_UALs = list(set(UALs))

            return {
                "Classification": classification,
                "SPARQL": query,
                "Response": {
                    "Text": response,
                    "UALs": unique_UALs,  # Return the list with duplicates removed
                }
            }
        else:
            print("Classification key missing in response")
            return {
                "Classification": 'Error',
                "SPARQL": '',
                "Response": {
                    "Text": '',
                    "UALs": [],
                }
            }

    except Exception as e:
        print(f"Error occurred: {e}")
        return {
            "Classification": 'Error',
            "SPARQL": '',
            "Response": {
                "Text": '',
                "UALs": [],
            }
        }


@timed_function
def similarity_search(question, milvus_client, collection_name):
    # Convert question to embedding
    query_embedding = convert_to_embeddings([question])[0]

    # Define output fields based on the collection
    output_fields = ["EntityID", "RAG", "UAL"] if collection_name == "EntityCollection" else ["combined"]

    # Perform search for the query embedding
    try:
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        res = milvus_client.search(
            collection_name=collection_name,
            data=[query_embedding],
            output_fields=output_fields,
            limit=5,
            search_params=search_params
        )
        # Adjust the following line based on the actual format of res
        return [hit.entity if hasattr(hit, 'entity') else hit for hit in res[0]]
    except Exception as e:
        print(f"Error during Milvus similarity search: {e}")
        return []

def format_query_result(query_results):
    """
    Returns a formatted string representation of a list of query results.
    Each item in the list is a dictionary.
    """
    formatted_results = ""
    for item in query_results:
        formatted_item = ', '.join(f"{key}: {value}" for key, value in item.items())
        formatted_results += "<br>" + formatted_item
    return formatted_results

def summarizeForTwitter(prompt: str, response: str) -> (str):
    try:
        # Call the OpenAI ChatCompletion API
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You should summarize the given response to the given prompt for Twitter."
                        "Your response MUST be less than 280 characters.  Do not include hastags.  It should be a one or two sentence summary."
                    )
                },
                {
                    "role": "user",
                    "content": f"prompt: '{prompt}', response: '{response}'"
                },
            ]
        )

        # Log token usage for cost estimation
        completion_tokens = completion.usage.completion_tokens
        prompt_tokens = completion.usage.prompt_tokens
        OpenAICallCost = 0.0005*prompt_tokens/1000 + 0.0015*completion_tokens/1000
        print(f"summarizeForTwitter.  input tokens: {prompt_tokens}, output tokens: {completion_tokens}, cost: {OpenAICallCost}")
        openAIresponse = completion.choices[0].message.content
        return openAIresponse
    except Exception as e:
        print(f"Error occurred: {e}")
        return 'Error', '', ''

@timed_function
async def process_query_for_twitter(question, history):
    pprint("Starting RAGandSPARQL with question: " + question)
    ontology_file_path = "Ontology/ontology.ttl"
    ontology_content = read_ontology_file(ontology_file_path)
    
    executor = concurrent.futures.ThreadPoolExecutor()
    loop = asyncio.get_event_loop()

    initial_matches_task = loop.run_in_executor(executor, similarity_search, question, milvus_client, "EntityCollection")
    query_search_results_task = loop.run_in_executor(executor, similarity_search, question, milvus_client, "QueryCollection")
    
    initial_matches, query_search_results = await asyncio.gather(initial_matches_task, query_search_results_task)

    # Adjusted to expect a single dictionary return
    response_data = await loop.run_in_executor(executor, extract_entities_and_classify, question, query_search_results, initial_matches, ontology_content, history)
    
    final_response = {"Text": ""}
    classification = response_data.get("Classification", "Error")

    # Always attempt to include a RAG response
    rag_response = response_data.get("Response", {}).get("Text", "")
    UALs = response_data.get("Response", {}).get("UALs", [])
    if rag_response:
        final_response["Text"] += "\n" + rag_response
        if UALs:
            # Prepare the prefix for the UAL links
            ual_prefix = "https://dkg.origintrail.io/explore?ual="
            # Convert each UAL to an HTML link
            links = [f'<a href="{ual_prefix}{ual}">{ual}</a>' for ual in UALs]
            # Join the links with HTML line breaks for display
            links_str = "<br>".join(links)
            # Add a double line break and space before "Knowledge Assets:"
            final_response["Text"] += "<br><br>Knowledge Assets:<br>" + links_str

    # Include SPARQL query if present
    if classification == "SPARQL" or response_data.get("SPARQL"):
        query = response_data.get("SPARQL", "")
        if query:
            query_with_prefixes = prepend_ontology_prefixes(query, ontology_content)
            sparql_results = execute_sparql_query(query_with_prefixes)
            if sparql_results:
                formatted_results = format_query_result(sparql_results)
                final_response["Text"] += "Results:\n" + formatted_results
            else:
                final_response["Text"] += "No results found."
        else:
            final_response["Text"] += "SPARQL query was expected but not provided."

    if not final_response["Text"].strip():
        final_response = {"Text": "No results found."}

    final_response_twitter = await loop.run_in_executor(executor, summarizeForTwitter, question, final_response["Text"])
    
    return {"final_response": final_response["Text"], "final_response_twitter": final_response_twitter}

    
if __name__ == "__main__":
    import sys

    question = sys.argv[1] if len(sys.argv) > 1 else "Enter your question here"

    result = asyncio.run(process_query_for_twitter(question, []))

    print("Final result: ")
    print(result)