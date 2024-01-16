from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
import json
from pprint import pprint

# Connect using a MilvusClient object
from pymilvus import MilvusClient
CLUSTER_ENDPOINT='https://in03-abeea0d9f89e792.api.gcp-us-west1.zillizcloud.com'
TOKEN='37f1e89f4f40987e852c30eaac731a40954c3a25c0455b97c993d1b62b35ecff347977c8fd7b79e009650390d0ca158e683fa746'

client = MilvusClient(
    uri=CLUSTER_ENDPOINT,  # Cluster endpoint obtained from the console
    token=TOKEN  # API key or a colon-separated cluster username and password
)

# Initialize the Sentence Transformer model
MODEL_NAME = 'sentence-transformers/multi-qa-MiniLM-L6-cos-v1'
model = SentenceTransformer(MODEL_NAME)

# Function to convert a list of strings to embeddings
def convert_to_embeddings(strings):
    return model.encode(strings, convert_to_tensor=True).numpy().tolist()

# List of strings to search
queries = [
    "Can you provide a full list of ReFi projects, initiatives and people connected to Spain?",
    "Spain"]

# Convert strings to embeddings
query_embeddings = convert_to_embeddings(queries)

# Perform search for each query embedding
for query, embedding in zip(queries, query_embeddings):
    res = client.search(
        collection_name="EntityCollection",
        data=[embedding],
        output_fields=["EntityID", "RAG", "UAL"],  # Replace with your output fields
        limit=5
    )
    print(f"Results for query: '{query}'")
    pprint(res)
    print("\n")  # Print a newline for better readability between results