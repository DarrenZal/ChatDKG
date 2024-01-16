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


@timed_function
def extract_entities_and_classify(question: str, ontology_content, history, initial_matches) -> (list, str, str, str):
    try:
        # Prepare initial_matches for the API call
        formatted_matches = ', '.join([f"'{match}'" for match in initial_matches])
        # Call the OpenAI ChatCompletion API
        completion = client.chat.completions.create(
    model="gpt-4-1106-preview",
    temperature=0.2,
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
                "Responses must be in JSON format. Example: "
                "For 'How many organizations received over $1000 in funding?', return '{\"Classification\": \"SPARQL\", \"SPARQL\": \"SELECT ?organization (SUM(?amount) AS ?totalFunding) WHERE { ?organization a schema:Organization. ?investment schema:investee ?organization. ?investment schema:amount ?amount. } GROUP BY ?organization HAVING (SUM(?amount) > 1000)\", \"Response\": {\"Text\": \"Relevant response\"}}'. "
                "For RAG: 'Who is Monty Merlin?' with RAGdata containing Monty Merlin's ID, use the ID to build an accurate SPARQL query."
            )
        },
        {
            "role": "user",
            "content": f"prompt: '{question}', RAGdata: {formatted_matches}, Ontology: '{ontology_content}'"
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
        classification = data["Classification"]
        query = data.get("SPARQL", '')
        responseRAG = data.get("Response", '')  # Capture the additional text response

        return classification, query, responseRAG

    except Exception as e:
        print(f"Error occurred: {e}")
        return [], [], ''  # Return empty lists and string if an error occurs

@timed_function
def similaritySearch(question, milvus_client):
    # Convert question to embedding
    query_embedding = convert_to_embeddings([question])

    # Perform search for the query embedding
    try:
        res = milvus_client.search(
            collection_name="EntityCollection",
            data=query_embedding,
            output_fields=["EntityID", "RAG", "UAL"],  # Replace with your output fields
            limit=10
        )
        return res
    except Exception as e:
        print(f"Error during Milvus search: {e}")
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

    # First, run similaritySearch
    initial_matches = await loop.run_in_executor(executor, similaritySearch, question, milvus_client)
    print("initial_matches: ")
    pprint(initial_matches)

    # Then, pass the results to extract_entities_and_classify
    classification, query, responseRAG = await loop.run_in_executor(executor, extract_entities_and_classify, question, ontology_content, history, initial_matches)

    pprint("responseRAG")
    pprint(responseRAG)

    """ print("Extracted Entities: ")
    pprint(entities) """
    print("Classification: ")
    pprint(classification)

    if classification == "SPARQL":

        # Amend the query with necessary prefixes from the ontology
        query = prepend_ontology_prefixes(query, ontology_content)

        # Handle entity resolution and query modification if entities are returned
        """ if entities:
            # Run similaritySearch for each entity in the executor and await the results
            entity_search_tasks = [loop.run_in_executor(executor, similaritySearch, entity, vector_db_entities) for entity in entities]
            entity_search_results = await asyncio.gather(*entity_search_tasks)

            # Modify the query with entity_search_results if necessary
            query = modify_query_with_entities(query, entity_search_results, ontology_content) """

        """ print("SPARQL query: ")
        pprint(query) """

        # Initialize DKG
        ot_node_hostname = os.getenv("OT_NODE_HOSTNAME") + ":8900"
        node_provider = NodeHTTPProvider(ot_node_hostname)
        blockchain_provider = BlockchainProvider(
                os.getenv("RPC_ENDPOINT"), 
                os.getenv("WALLET_PRIVATE_KEY")
            )

        # initialize the DKG client on OriginTrail DKG
        dkg = DKG(node_provider, blockchain_provider)

        print("query: ")
        pprint(query)

        def format_query_result(item):
            # Returns a formatted string representation of a single query result
            # using <br> for line breaks in HTML
            return '<br>' + ', '.join(f"{key}: {value}" for key, value in item.items())

        query_graph_result = dkg.graph.query(query, repository="privateCurrent")
        print("query_graph_result: ", query_graph_result)

        formatted_results = [format_query_result(item) for item in query_graph_result]

        # Combine responseRAG with formatted_results if responseRAG is not blank
        final_result = {
            "Text": responseRAG if responseRAG else "",
            "Details": formatted_results
        }

        executor.shutdown()
        return final_result
    if classification == "RAG":
        executor.shutdown()
        return {"Text": responseRAG}
    
if __name__ == "__main__":
    import sys

    # Get the question from command line argument
    question = sys.argv[1]

    # Correctly running the async function
    result = asyncio.run(RAGandSPARQL(question, ''))

    print("result: ")
    print(result)