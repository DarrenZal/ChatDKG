import time
start_time = time.time()
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Milvus
from dkg import DKG
from dkg.providers import BlockchainProvider, NodeHTTPProvider
import re
from pprint import pprint
from pymilvus import MilvusClient
import asyncio
import concurrent.futures
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

embedding_model = "multi-qa-MiniLM-L6-cos-v1"

embedding_function = HuggingFaceEmbeddings(model_name=embedding_model)

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

# Initializing VectorDB connection which was pre-populated with Knowledge Asset vector embeddings
vector_db_entities = Milvus(
    collection_name="EntityCollection",
    embedding_function=HuggingFaceEmbeddings(model_name="multi-qa-MiniLM-L6-cos-v1"),
    connection_args={
            "uri": os.getenv("MILVUS_URI"),
            "token": os.getenv("MILVUS_TOKEN"),
            "secure": True,
        },
)

vector_db_relations = Milvus(
    collection_name="RelationCollection",
    embedding_function=HuggingFaceEmbeddings(model_name="multi-qa-MiniLM-L6-cos-v1"),
    connection_args={
            "uri": os.getenv("MILVUS_URI"),
            "token": os.getenv("MILVUS_TOKEN"),
            "secure": True,
        },
)

@timed_function
def extract_entities_and_classify(question: str, ontology_content, history) -> (list, str, str):
    try:
        # Call the OpenAI ChatCompletion API
        completion = client.chat.completions.create(
            model="gpt-4-1106-preview",
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                    "This system is for a ReFi chatbot. ReFi stands for Regenerative Finance, "
                    "an ecosystem in web3. You will receive a natural language prompt. Extract relevant "
                    "entities with attributes, and classify the prompt as 'SPARQL' or 'RAG'. 'SPARQL' "
                    "means the prompt should be answered via a SPARQL query using the provided OWL ontology.  Only use subject and object types in accordance with the domain and range of objectProperties / link types. "
                    "'RAG' means the prompt is better answered by retrieval augmented generation. For all "
                    "SPARQL queries, regardless of user phrasing, the returned query must aggregate total "
                    "values before applying filters, and include details such as  "
                    "IDs for clarity and data provenance. Use subqueries if necessary. "
                    "Responses must be formatted as JSON. Here is an example:: 'How many organizations "
                    "have received more than $1000 in funding?' should be answered as '{\"Classification\": "
                    "\"SPARQL\", \"SPARQL\": \"SELECT ?organization (SUM(xsd:decimal(?amount)) AS "
                    "?totalFunding) WHERE { ?organization a schema:Organization . "
                    " ?investment a schema:InvestmentOrGrant . ?investment schema:investee "
                    "?organization . ?investment schema:amount ?amount . } GROUP BY ?organization "
                    "HAVING (SUM(xsd:decimal(?amount)) > 1000)\"}'. Example for RAG: 'Who is James Nash?' should "
                    "be classified and answered with an empty SPARQL as '{\"Classification\": \"RAG\", \"SPARQL\": \"\"}'."
                    )
                },
                {
                    "role": "user",
                    "content": f"prompt: '{question}', Ontology: '{ontology_content}'"
                },
                *history # Include chat history in the API call
            ]
        )

        # Extract the response content
        extracted_content = completion.choices[0].message.content
        data = json.loads(extracted_content)
        print((data))

        # Process entities
        """ for entity_name, attributes in data["Entities"].items():
            entity_str = f"{entity_name}: "
            for attr, value in attributes.items():
                entity_str += f"{attr}:{value}; "
            entities.append(entity_str.rstrip('; '))  # Remove trailing semicolon

        entities = list(set(entities)) """
        classification = data["Classification"]
        query = data.get("SPARQL", '')

        return classification, query

    except Exception as e:
            print(f"Error occurred: {e}")
            return [], []  # Return empty lists if an error occurs

@timed_function
def similaritySearch(question, vector_db):
    client = MilvusClient(
        uri= os.getenv("MILVUS_URI"),
        token= os.getenv("MILVUS_TOKEN") 
    )
    """ res = client.query(
        collection_name="EntityCollection",
        filter='(EntityID == "https://example.com/urn:content:BlockchainforScalingClimateActionWorldEconomicForumWEF")',
        output_fields=["EntityID", "text", "RAG"]
    )

    print(res) """

    matches = vector_db.similarity_search(question)
    if matches:  # Check if there is at least one match
        return matches[:5] # Append only the top 10 results

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
def RAG(question, matches, additional_matches, history):
    # Format the matches for sending to OpenAI's API
    formatted_matches = ', '.join([f"'{match}'" for match in matches])

    try:
        # Call the OpenAI ChatCompletion API with the question and matches
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": "Generate a response for a chatbot based on the prompt, the provided semantic search results for the prompt and entities exrtacted from the prompt, and your own knowledge. Provide just the response."
                },
                {
                    "role": "user",
                    "content": f"Question: '{question}'. Question Matches: {formatted_matches}. Entity Matches: {additional_matches}"
                },
                *history # Include chat history in the API call
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return "Error generating RAG response."

@timed_function
async def RAGandSPARQL(question, history):
    ontology_file_path = "ontology.ttl"
    ontology_content = read_ontology_file(ontology_file_path)
    
    # Create a thread pool executor
    executor = concurrent.futures.ThreadPoolExecutor()
    
    # Get the current event loop
    loop = asyncio.get_event_loop()

    # Run extract_entities_and_classify and similaritySearch in the executor
    extract_task = loop.run_in_executor(executor, extract_entities_and_classify, question, ontology_content, history)
    semantic_search_task = loop.run_in_executor(executor, similaritySearch, question, vector_db_entities)

    classification, query = await extract_task
    initial_matches = await semantic_search_task

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
        query_graph_result = dkg.graph.query(
            query,
            repository="privateCurrent",
        )
        print("query_graph_result: ")
        pprint(query_graph_result)
        executor.shutdown()
        return str(query_graph_result)
    if classification == "RAG":
        additional_matches = {}
        """ if entities:
            # Run similaritySearch for each entity in the executor and gather the results
            entity_search_tasks = [loop.run_in_executor(executor, similaritySearch, entity, vector_db_entities) for entity in entities]
            entity_search_results = await asyncio.gather(*entity_search_tasks)
            
            # Format the results for additional matches
            additional_matches = {entity: result for entity, result in zip(entities, entity_search_results)} """

        # Call the RAG function with the original question, initial matches, and additional entity matches
        rag_response = RAG(question, initial_matches, additional_matches, history)
        print("RAG Response: ")
        pprint(rag_response)
        executor.shutdown()
        return rag_response

if __name__ == "__main__":
    import sys

    # Get the question from command line argument
    question = sys.argv[1]

    # Correctly running the async function
    result = asyncio.run(RAGandSPARQL(question))

    print("result: ")
    print(result)