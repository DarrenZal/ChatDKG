import os
import pandas as pd
from pymilvus import connections, DataType, FieldSchema, CollectionSchema, Collection, utility
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Milvus connection and collection setup
uri = os.getenv("MILVUS_URI_MAINNET")
token = os.getenv("MILVUS_TOKEN_MAINNET")
collection_name = 'EntityCollection'
DIMENSION = 384  # Dimension of embeddings

# Connect to Milvus
connections.connect(uri=uri, token=token, secure=True)

# Define the embedding model
embedding_model = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
model = SentenceTransformer(embedding_model)

def create_collection_schema(df, collection_name):
    fields = [FieldSchema(name='id', dtype=DataType.INT64, is_primary=True, auto_id=True)]
    for col in df.columns:
        if col != 'NER':  # Exclude 'NER' field
            fields.append(FieldSchema(name=col, dtype=DataType.VARCHAR, max_length=65535))
    fields.append(FieldSchema(name='vector', dtype=DataType.FLOAT_VECTOR, dim=DIMENSION))  # Embedding column
    schema = CollectionSchema(fields)
    collection = Collection(name=collection_name, schema=schema)
    return collection

def tokenize_and_embed(text):
    encoded_input = model.encode(text, convert_to_tensor=True)
    return encoded_input.cpu().numpy().tolist()

# Read TSV
df = pd.read_csv('entitiesMainnet.tsv', sep='\t')

# Check if the collection already exists
if utility.has_collection(collection_name):
    collection = Collection(name=collection_name)
    print(f"Collection '{collection_name}' already exists. Dropping it.")
    utility.drop_collection(collection_name)

# Create the collection since it either doesn't exist or was just dropped
collection = create_collection_schema(df, collection_name)
print(f"Collection '{collection_name}' created.")

# Indexing parameters
index_params = {
    'metric_type': 'L2',
    'index_type': 'AUTOINDEX',
    'params': {}
}

# Create index and load collection
collection.create_index(field_name='vector', index_params=index_params)
collection.load()

# Prepare and insert data into Milvus
insert_data = {col: [] for col in df.columns if col != 'NER'}
insert_data['vector'] = []

for _, row in df.iterrows():
    for col in df.columns:
        if col != 'NER':
            insert_data[col].append(row[col])
    insert_data['vector'].append(tokenize_and_embed(row['NER']))

# Insert data
collection.insert([insert_data[col] for col in insert_data])

print("Data uploaded successfully.")
