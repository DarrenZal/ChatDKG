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
    

async def generate_RAG_response(question, initial_matches):
    try:
        # Format initial_matches for API call
        formatted_matches = ', '.join([f"'{match}'" for match in initial_matches])

        # Call the OpenAI ChatCompletion API
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            temperature=0.1,  # Adjust as needed
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assisting with prompts about Regenerative Finance (ReFi). Generate a response based on the given question and use your own knowledge and any relevant data found in the included RAG Search Results. Ignore any of the Search Results that are irrelevant to the prompt. Format the response with HTML line breaks (<br>) for use in HTML."
                },
                {
                    "role": "user",
                    "content": f"Prompt: '{question}', Search Results: {formatted_matches}"
                }
            ]
        )

        # Extract the text response and replace '\n' with '<br>'
        response = completion.choices[0].message.content.replace("\n", "<br>")

        completion_tokens = completion.usage.completion_tokens
        prompt_tokens = completion.usage.prompt_tokens
        total_tokens = completion.usage.total_tokens
        OpenAICallCost = 0.001*prompt_tokens/1000 + 0.002*completion_tokens/1000
        print(f"generate_RAG_response.  input tokens: {prompt_tokens}, output tokens: {completion_tokens}, cost: {OpenAICallCost}")

        return response

    except Exception as e:
        print(f"Error during LLM response generation: {e}")
        return "Sorry, I encountered an error while processing your request."


@timed_function
def extract_entities_and_classify(question: str, query_matches, ontology_content, history) -> (str, str):
    try:
        # Format the query matches for the prompt
        formatted_matches = ", ".join([f"Query Match: {match}" for match in query_matches])

        # Call the OpenAI ChatCompletion API
        completion = client.chat.completions.create(
            model="gpt-4-1106-preview",
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "This system is for a ReFi chatbot focused on Regenerative Finance in web3. "
                        "Upon receiving a natural language prompt, classify it as 'SPARQL' or 'RAG'. "
                        "'SPARQL' prompts should be answered with a SPARQL query using a provided OWL ontology, respecting objectProperties' domain and range. "
                        "'RAG' prompts are better suited for retrieval augmented generation. "
                        "For RAG queries, if relevant, provide a 'Response' object for user display. "
                        "If SPARQL is relevant for a RAG query, especially when RAGdata (similarity search results) contains useful entity information, construct a SPARQL query utilizing this data. "
                        "For SPARQL queries, ensure aggregation of total values before applying filters, and include details like IDs or names for clarity. "
                        "Consider the inlcuded SPARQL query matches from the database when creating the query. "
                        "Responses must be in JSON format. Example: "
                        "For 'How many organizations received over $1000 in funding?', return '{\"Classification\": \"SPARQL\", \"SPARQL\": \"SELECT ?organization (SUM(?amount) AS ?totalFunding) WHERE { ?organization a schema:Organization. ?investment schema:investee ?organization. ?investment schema:amount ?amount. } GROUP BY ?organization HAVING (SUM(?amount) > 1000)\", \"Response\": {\"Text\": \"Relevant response\"}}'. "
                        "For RAG: 'Who is Monty Merlin?' with RAGdata containing Monty Merlin's ID, use the ID to build an accurate SPARQL query."
                    )
                },
                {
                    "role": "user",
                    "content": f"prompt: '{question}', Query Matches: '{formatted_matches}', Ontology: '{ontology_content}'"
                },
                *history  # Include chat history in the API call
            ]
        )

        # Extract the response content
        extracted_content = completion.choices[0].message.content
        data = json.loads(extracted_content)
        print("Response data")
        print(data)

        # Extract additional information from the response
        classification = data.get("Classification", "Error")
        query = data.get("SPARQL", '')

        # Handle missing Classification key
        if classification == "Error":
            print("Classification key missing in response")
            return 'Error', ''

        # Log token usage for cost estimation
        completion_tokens = completion.usage.completion_tokens
        prompt_tokens = completion.usage.prompt_tokens
        OpenAICallCost = 0.01*prompt_tokens/1000 + 0.03*completion_tokens/1000
        print(f"extract_entities_and_classify.  input tokens: {prompt_tokens}, output tokens: {completion_tokens}, cost: {OpenAICallCost}")

        return classification, query

    except Exception as e:
        print(f"Error occurred: {e}")
        return 'Error', ''  # Return default values if an error occurs


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

@timed_function
def modify_query_with_entities(query: str, entity_search_results, ontology_content) -> str:
    try:
        # Call the OpenAI ChatCompletion API
        completion = client.chat.completions.create(
            model="gpt-4-1106-preview",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": "You are given a SPARQL query, and Ontology for the db, and a list of entities along with their attributes which were matched to extracted entities in the prompt.  Your job is to modify the SPARQL query if necessary to maximize the accuracy of answering the prompt.  Provide just the SARQL query text as a response."
                    "Example: 'How many organizations have received more than $100 in total funding, and what are their names?': {'Entities': {'Entity1': {'@type': 'Organization'}}, 'Classification': 'SPARQL', 'SPARQL': 'SELECT ?organization (SUM(xsd:decimal(?amount)) as ?totalFunding) WHERE { ?organization a schema:Organization . ?investment a schema:InvestmentOrGrant . ?investment schema:investee ?organization . ?investment schema:amount ?amount . } GROUP BY ?organization HAVING SUM(xsd:decimal(?amount)) > 100 }'}"
                },
                {
                    "role": "user",
                    "content": f"query: '{query}', entity_search_results: '{entity_search_results}', ontology_content: '{ontology_content}"
                }  
            ]
        )

        # Extract the SPARQL query from the response
        response = completion.choices[0].message.content

        # Remove Markdown code block formatting and any leading non-query text
        query_text = response.strip('`')
        query_text = query_text.replace('sparql\n', '').strip()

        return query_text

    except Exception as e:
        print(f"Error occurred: {e}")
        return ''  # Return empty string if an error occurs

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
    pprint("history")
    pprint(history)
    ontology_file_path = "Ontology/ontology.ttl"
    ontology_content = read_ontology_file(ontology_file_path)
    
    # Create a thread pool executor
    executor = concurrent.futures.ThreadPoolExecutor()
    
    # Get the current event loop
    loop = asyncio.get_event_loop()

    # First, run similarity search on EntityCollection
    initial_matches_task = loop.run_in_executor(executor, similarity_search, question, milvus_client, "EntityCollection")
    
    # Also, run similarity search on QueryCollection
    query_search_results_task = loop.run_in_executor(executor, similarity_search, question, milvus_client, "QueryCollection")
    
    # Wait for both similarity searches to complete
    initial_matches, query_search_results = await asyncio.gather(initial_matches_task, query_search_results_task)
    print("initial_matches: ")
    pprint(initial_matches)


    print("top_queries: ")
    pprint(query_search_results)

    # Run extract_entities_and_classify with top query search results
    extract_task = loop.run_in_executor(executor, extract_entities_and_classify, question, query_search_results, ontology_content, history)
    
    # Continue with the existing RAG response using the EntityCollection
    rag_task = generate_RAG_response(question, initial_matches)  # Assuming this is an async function
    results = await asyncio.gather(extract_task, rag_task)

    # Unpack the results
    classification, query = results[0]
    rag_response = results[1]

    print("Classification: ")
    pprint(classification)


    final_response = {"Text": "An error occurred."}
    if classification == "SPARQL":
        query = prepend_ontology_prefixes(query, ontology_content)
        try:
            sparql_results = execute_sparql_query(query)
            print("SPARQL results:", sparql_results)  # Debugging log

            if sparql_results:
                formatted_results = format_query_result(sparql_results)
                print("Formatted SPARQL results:", formatted_results)  # Debugging log
                final_response = {"Text": rag_response + "<br>" + "\nSPARQL Results:\n" + formatted_results}
            else:
                final_response = {"Text": rag_response}

        except Exception as e:
            print("Error processing SPARQL response:", e)  # Error log
            final_response = {"Text": "An error occurred processing the SPARQL response."}

    elif classification == "RAG":
        final_response = {"Text": rag_response}

    executor.shutdown()
    return final_response
    
if __name__ == "__main__":
    import sys

    # Get the question from command line argument
    question = sys.argv[1]

    # Correctly running the async function
    result = asyncio.run(RAGandSPARQL(question, ''))

    print("result: ")
    print(result)