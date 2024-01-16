import os
import pandas as pd
from pymilvus import connections, DataType, FieldSchema, CollectionSchema, Collection, utility
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Milvus connection and collection setup
uri = os.getenv("MILVUS_URI")
token = os.getenv("MILVUS_TOKEN")
collection_name = 'QueryCollection'
DIMENSION = 384  # Dimension of embeddings

# Connect to Milvus
connections.connect(uri=uri, token=token, secure=True)
utility.drop_collection("QueryCollection")

# Define the embedding model
embedding_model = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
model = SentenceTransformer(embedding_model)

def create_collection_schema(df, collection_name):
    fields = [FieldSchema(name='id', dtype=DataType.INT64, is_primary=True, auto_id=True)]
    for col in df.columns:
        if col == 'combined':  # The new combined column
            fields.append(FieldSchema(name=col, dtype=DataType.VARCHAR, max_length=65535))
    fields.append(FieldSchema(name='vector', dtype=DataType.FLOAT_VECTOR, dim=DIMENSION))  # Embedding column
    schema = CollectionSchema(fields=fields)
    collection = Collection(name=collection_name, schema=schema)
    return collection

def tokenize_and_embed(text):
    encoded_input = model.encode(text, convert_to_tensor=True)
    return encoded_input.cpu().numpy().tolist()

# Read TSV and modify the dataframe
df = pd.read_csv('queries.tsv', sep='\t')
df['combined'] = df.apply(lambda row: f"question: {row['question']}; query: {row['query']}", axis=1)

collection = create_collection_schema(df, collection_name)

# Indexing parameters
index_params = {
    'metric_type': 'L2',
    'index_type': 'AUTOINDEX',
    'params': {}
}

collection.create_index(field_name='vector', index_params=index_params)
collection.load()

# Prepare and insert data into Milvus
insert_data = {col: [] for col in df.columns if col == 'combined'}
insert_data['vector'] = []

for _, row in df.iterrows():
    insert_data['combined'].append(row['combined'])
    insert_data['vector'].append(tokenize_and_embed(row['query']))

collection.insert([insert_data[col] for col in insert_data])

print("Data uploaded successfully.")
