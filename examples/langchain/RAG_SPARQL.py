import time
start_time = time.time()
import os
import json
import asyncio
import concurrent.futures
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
CLUSTER_ENDPOINT = os.getenv("MILVUS_URI")
TOKEN = os.getenv("MILVUS_TOKEN")
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
        ot_node_hostname = os.getenv("OT_NODE_HOSTNAME") + ":8900"
        node_provider = NodeHTTPProvider(ot_node_hostname)
        blockchain_provider = BlockchainProvider(
            os.getenv("RPC_ENDPOINT"), 
            os.getenv("WALLET_PRIVATE_KEY")
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
def extract_entities_and_classify(question: str, query_matches, entity_matches, ontology_content, history) -> (str, str, str):
    try:
        # Format the query matches for the prompt
        formatted_query_matches = ", ".join([f"Query Match: {match}" for match in query_matches])
        # Format the entity matches for the prompt
        formatted_entity_matches = ", ".join([f"Query Match: {match}" for match in entity_matches])

        # Call the OpenAI ChatCompletion API
        completion = client.chat.completions.create(
            model="gpt-4-0125-preview",
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "This system is for a ReFi chatbot to answer questions about Regenerative Finance (ReFi). "
                        "Upon receiving a natural language prompt, classify it as 'SPARQL' or 'RAG'. "
                        "'SPARQL' means the prompt is answerable with a SPARQL query using a provided OWL ontology, respecting objectProperties' domain and range, as well as any relevant data from Entity Matches."
                        "'RAG' means the prompt is better suited for retrieval augmented generation with relevant search results in Entity Matches as well as your own knowledge."
                        "For RAG, Ignore any of the Entity Matches that are irrelevant to the prompt. Also, Format the response with HTML line breaks (<br>) for use in HTML."
                        "For RAG, provide a 'Response' object for user display. "
                        "For SPARQL queries, ensure aggregation of total values before applying filters, and include details like IDs or names for clarity. "
                        "Retrieve all attributes for a subject in question when possible, ie retrieve more info than necessary"
                        "Consider the included SPARQL query matches 'Query Matches' from the database when creating the query. "
                        "Responses must be in JSON format. Example: "
                        "For 'How many organizations received over $1000 in funding?', return '{\"Classification\": \"SPARQL\", \"SPARQL\": \"SELECT ?organization (SUM(?amount) AS ?totalFunding) WHERE { ?organization a schema:Organization. ?investment schema:investee ?organization. ?investment schema:amount ?amount. } GROUP BY ?organization HAVING (SUM(?amount) > 1000)\", \"Response\": {\"Text\": \"Relevant response\"}}'. "
                        "For RAG: 'Who is Monty Merlin?' with RAGdata containing Monty Merlin's ID, use the ID to build a SPARQL query to retreive all of this entity's attribues."
                        "For SPARQL: 'What is the phone number of ExampleDAO?' with RAGdata containing ExampleDAO's ID, use the ID to build a SPARQL query to retreive all of this entity's attribues."
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
        OpenAICallCost = 0.03*prompt_tokens/1000 + 0.06*completion_tokens/1000
        print(f"extract_entities_and_classify.  input tokens: {prompt_tokens}, output tokens: {completion_tokens}, cost: {OpenAICallCost}")

        extracted_content = completion.choices[0].message.content
        print("Extracted Content:", extracted_content)  # You have this for debugging.
        data = json.loads(extracted_content)
        
        classification = data.get("Classification", "Error")
        if classification == "Error":
            print("Classification key missing in response")
            return 'Error', '', ''

        # Adjust handling here based on the actual structure of "Response"
        if classification == "SPARQL":
            query = data.get("SPARQL", '')
            return classification, query, ''
        elif classification == "RAG":
            # Directly use the response string if classification is "RAG"
            response = data.get("Response", "")  # Assuming "Response" is a string.
            return classification, '', response
        else:
            return 'Error', '', ''
    except Exception as e:
        print(f"Error occurred: {e}")
        return 'Error', '', ''


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

@timed_function
async def RAGandSPARQL(question, history):
    pprint("Starting RAGandSPARQL with question: " + question)
    ontology_file_path = "Ontology/ontology.ttl"
    ontology_content = read_ontology_file(ontology_file_path)
    ontology_content = ""
    
    # Create a thread pool executor
    executor = concurrent.futures.ThreadPoolExecutor()
    
    # Get the current event loop
    loop = asyncio.get_event_loop()

    # Run similarity search on EntityCollection and QueryCollection in parallel
    initial_matches_task = loop.run_in_executor(executor, similarity_search, question, milvus_client, "EntityCollection")
    query_search_results_task = loop.run_in_executor(executor, similarity_search, question, milvus_client, "QueryCollection")
    
    # Wait for both similarity searches to complete
    initial_matches, query_search_results = await asyncio.gather(initial_matches_task, query_search_results_task)

    # Now, only call extract_entities_and_classify (which also handles RAG response internally)
    classification, query, rag_response = await loop.run_in_executor(executor, extract_entities_and_classify, question, query_search_results, initial_matches, ontology_content, history)

    final_response = {"Text": "An error occurred."}
    if classification == "SPARQL":
        # If the classification is SPARQL, prepend ontology prefixes and execute the SPARQL query
        query_with_prefixes = prepend_ontology_prefixes(query, ontology_content)
        sparql_results = execute_sparql_query(query_with_prefixes)

        if sparql_results:
            formatted_results = format_query_result(sparql_results)
            final_response = {"Text": "SPARQL Results:\n" + formatted_results}
        else:
            final_response = {"Text": "No SPARQL results found."}
    elif classification == "RAG":
        # If the classification is RAG, use the RAG response directly
        final_response = {"Text": rag_response}
    else:
        # Handle error or unexpected classification result
        final_response = {"Text": "An error occurred during processing."}

    executor.shutdown()
    return final_response
    
if __name__ == "__main__":
    import sys

    # Get the question from command line argument
    question = sys.argv[1] if len(sys.argv) > 1 else "Enter your question here"

    # Correctly running the async function
    result = asyncio.run(RAGandSPARQL(question, []))

    print("Final result: ")
    print(result)