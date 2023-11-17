import os
import openai
from dotenv import load_dotenv
import openai
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Milvus
load_dotenv()

embedding_model = "multi-qa-MiniLM-L6-cos-v1"

embedding_function = HuggingFaceEmbeddings(model_name=embedding_model)

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

# Set your OpenAI API key
openai.api_key = "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"

# Specific question
question = "What companies in the renewable energy sector have received investment from entities that also invested in BioGenX?"


def extract_entities_relations(question: str) -> (list, list):
    # Call the OpenAI ChatCompletion API
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview",
        messages=[
            {
                "role": "system",
                "content": "You receive a question and identify the named-entities and relations which will be needed to build a SPARQL query, which I will provide."
            },
            {
                "role": "user",
                "content": f"take this question {question} and extract the entities and relations which I will need to build a SPARQL query that answers the question. put the list of entities on a line with Entities: and relations with Relations:",
            },
        ],
    )

    # Extract the response content
    extracted_content = response['choices'][0]['message']['content']
    lines = extracted_content.split('\n')
    entities, relations = [], []
    current_key = None

    for line in lines:
        # Debug print to show each line being processed
        print(f"Processing line: {line}")

        # Check for the start of the entity or relation list
        if line.startswith("Entities:"):
            current_key = "Entities"
            # Directly add entities found on the same line as "Entities:"
            entities.extend(line.replace("Entities:", "").strip().split(', '))
            continue
        elif line.startswith("Relations:"):
            current_key = "Relations"
            # Directly add relations found on the same line as "Relations:"
            relations.extend(line.replace("Relations:", "").strip().split(', '))
            continue

        # Skip lines with SPARQL query or empty lines
        if '```' in line or not line.strip():
            current_key = None
            continue

        # Add items to the entities or relations list if within their respective sections
        if current_key == "Entities":
            entities.extend(line.split(', '))
        elif current_key == "Relations":
            relations.extend(line.split(', '))

    return entities, relations



def construct_sparql_query_openai(question: str, matched_entities: list, matched_relations: list) -> str:
    # Extract URNs or alternative fields from matched entities and relations
    entity_urns = []
    for entity in matched_entities:
        entity_urns.append(entity)
    
    relation_triples = []
    for relation in matched_relations:
        # Assuming each relation is a string containing a URL and a metadata dictionary
        subject_urn = relation.metadata['SubjectID']
        object_urn = relation.metadata['ObjectID']
        # Construct the triple pattern using the correct directionality
        triple = f"<{subject_urn}> <{relation.page_content}> <{object_urn}>"
        relation_triples.append(triple)

    print("entity_urns: ", entity_urns)
    print("relation_triples: ", relation_triples)

    # Call the OpenAI ChatCompletion API
    response = openai.ChatCompletion.create(
        model="gpt-4-1106-preview",
        messages=[
            {
                "role": "system",
                "content": "You are to construct a SPARQL query based on a natural language question and given entities and relations. Convert the question's structure into a SPARQL query format, including the directionality of relationships.  Use full IRIs where possible, and minimize prefixes."
            },
            {
                "role": "user",
                "content": f"Construct a SPARQL query for the question '{question}' using full IRIs/IDs for entities {entity_urns} and taking into account relation types and literals from  {relation_triples} which contain context for directionality.  Use full IRIs for entities if possible. Give me only the SPARQL query as an output.",
            },
        ],
    )
    return response['choices'][0]['message']['content']


""" # Function to convert distance to similarity score, if needed
def convert_distance_to_similarity(distance):
    # Modify this conversion to fit your use case
    similarity = 1 / (1 + distance)
    return similarity

# Function to embed text using the HuggingFace model
def embed(text):
    # Directly calling the 'embedding_function' object if it is callable.
    # This is common in Hugging Face's transformers where the model object can be called directly.
    return embedding_function(text)[0]


# Function to insert data into your vector database
def insert_data(collection, data):
    for idx, text in enumerate(data):
        # Embed the text
        embedding = embed(text)
        # Insert the title id, the title text, and the title embedding vector
        ins = [[idx], [(text[:198] + '..') if len(text) > 200 else text], [embedding]]
        collection.insert(ins)
        time.sleep(3)  # Adjust as per your rate limits

# Function to search the vector database
def search(text, collection):
    search_params = {
        "metric_type": "L2"
    }
    
    # Generate the embedding for the search text
    query_embedding = embed(text)

    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=5,
        output_fields=['title']
    )
    
    return [(hit.id, convert_distance_to_similarity(hit.score), hit.entity.get('title')) for hit in results[0]] """

# Function to match entities with a similarity score threshold
""" def match_entities(entities, vector_db, score_threshold=0.8):
    matched_entities = []
    for entity in entities:
        if entity:  # Check if the entity string is not empty
            matches = search(entity, vector_db)
            for hit_id, similarity, title in matches:
                print(f"Entity: {entity}, Match Score: {similarity}")  # For testing
                if similarity >= score_threshold:
                    matched_entity = {
                        'EntityValue': entity,
                        'EntityID': hit_id,
                        'MatchScore': similarity,
                        'Title': title
                    }
                    matched_entities.append(matched_entity)
    return matched_entities """


def match_entities(entities, vector_db):
    matched_entities = []
    for entitie in entities:
        if entitie:  # Check if the relation string is not empty
            matches = vector_db.similarity_search(entitie)
            if matches:  # Check if there is at least one match
                matched_entities.append(matches[0])  # Append only the top result
    return matched_entities


def match_relations(relations, vector_db):
    matched_relations = []
    for relation in relations:
        if relation:  # Check if the relation string is not empty
            matches = vector_db.similarity_search(relation)
            if matches:  # Check if there is at least one match
                matched_relations.append(matches[0])  # Append only the top result
    return matched_relations


# Extract entities and relations
entities, relations = extract_entities_relations(question)

print("Extracted Entities: ", entities)
print("Extracted Relations: ", relations)

# Match the candidate entities and relations using vector similarity
matched_entities = match_entities(entities, vector_db_entities)
matched_relations = match_relations(relations, vector_db_relations)

print("Matched Entities: ", [str(entity) for entity in matched_entities])
print("Matched Relations: ", [str(relation) for relation in matched_relations])

# Construct the SPARQL query using OpenAI
sparql_query = construct_sparql_query_openai(question, matched_entities, matched_relations)
print(f"\nConstructed SPARQL Query: \n{sparql_query}")


# We obtain a list of relevant extracted Knowledge Assets for further exploration
""" print("EXTRACTED entities: \n")
print(json.dumps(all_entities, indent=4))

print("EXTRACTED relations: \n")
print(json.dumps(all_relations, indent=4)) """


# If we want to, we can submit the extracted results further to an LLM (OpenAI in this case) to obtain a summary of the extracted information

""" openai.api_key = os.getenv("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")

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "system", 
            "content": f"You receive a question and some JSON, and you answer the question based on the information found in the JSON. You do not mention the JSON in the response, but just produce an answer."
        },
        {
            "role": "user", 
            "content": f"Answer the question: {question} based on the following json: {json.dumps(all_documents)}",},
    ],
)

print("\n\nEXTRACTED & SUMMARIZED RESPONSES: \n")
print(response['choices'][0]['message']['content']) """
