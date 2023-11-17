import os
import json
from dotenv import load_dotenv

import openai
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Milvus

load_dotenv()


# Initializing VectorDB connection which was pre-populated with Knowledge Asset vector embeddings
vector_db_entities = Milvus(
    collection_name="EntitiesCollection",
    embedding_function=HuggingFaceEmbeddings(model_name="multi-qa-MiniLM-L6-cos-v1"),
    connection_args={
            "uri": os.getenv("MILVUS_URI"),
            "token": os.getenv("MILVUS_TOKEN"),
            "secure": True,
        },
)

vector_db_relations = Milvus(
    collection_name="RelationsCollection",
    embedding_function=HuggingFaceEmbeddings(model_name="multi-qa-MiniLM-L6-cos-v1"),
    connection_args={
            "uri": os.getenv("MILVUS_URI"),
            "token": os.getenv("MILVUS_TOKEN"),
            "secure": True,
        },
)

# We demonstrate vector similarity search with a simple demo question

# question = "What organizations is Tomer Bariach involved with?"
question = "What deals has ReFiDAO made?"

openai.api_key = "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"


def extract_entities_relations(question: str) -> (list, list):
    # Call the OpenAI ChatCompletion API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You receive a question, you identify the named-entities and relations in the question which will be used for named-entity and relation linking in order to convert the question into a SPARQL query.  For entities, onyl give a list of the named entities not the entities which are variables to be determined from the query."
            },
            {
                "role": "user",
                "content": f"Extract the entites and relations from this: {question}:",
            },
        ],
    )

    # Extract the response content
    extracted_content = response['choices'][0]['message']['content']
    
    # Split by newlines and then by colons to extract the entities and relations
    lines = extracted_content.split('\n')
    entities, relations = [], []
    current_key = None
    for line in lines:
        if "Entities:" in line:
            current_key = "Entities"
        elif "Relations:" in line:
            current_key = "Relations"
        else:
            if current_key == "Entities":
                entities.append(line.strip('- ').strip())
            elif current_key == "Relations":
                relations.append(line.strip('- ').strip())
            
    return entities, relations




def construct_sparql_query_openai(question: str, matched_entities: list, matched_relations: list) -> str:
    # Extract URNs or alternative fields from matched entities and relations
    entity_urns = []
    
    # Access the metadata of the first matched entity to retrieve the context
    context = matched_entities[0].metadata.get("@context", "http://schema.org/")  # Defaulting to schema.org if not found
    
    for entity in matched_entities:
        print("entity: ", entity)
        urn = entity.metadata.get('id', entity.page_content)
        entity_urns.append(urn)
    
    relation_urns = []
    for relation in matched_relations:
        urn = relation.metadata.get('id', relation.page_content)
        relation_urns.append(urn)

    # Convert simple relation names to full IRIs using the context
    full_iri_relations = [f"{context}{rel}" if not rel.startswith("http") else rel for rel in relation_urns]

    print("entity_urns: ", entity_urns)
    print("full_iri_relations: ", full_iri_relations)

    # Call the OpenAI ChatCompletion API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are to construct a SPARQL query based on a natural language question and given entities and relations. Convert the question's structure into a SPARQL query format. Please use full IRIs, not preficed IRIs."
            },
            {
                "role": "user",
                "content": f"Construct a SPARQL query for the question '{question}' using entities {entity_urns} and relations {full_iri_relations}. use full IRIs {full_iri_relations} in the Query, do not use preficed IRIs (PREFIX schema..)",
            },
        ],
    )

    # Extract the SPARQL query from the response content
    sparql_query = response['choices'][0]['message']['content']
    return sparql_query




# Extract entities and relations
entities, relations = extract_entities_relations(question)

# Filter out entities with a (variable) appended to them
entities_to_search = [entity for entity in entities if not entity.endswith("(variable)")]

print("Extracted Entities: ", entities)
print("Entities to Search: ", entities_to_search)
print("Extracted Relations: ", relations)

# Match the candidate entities and relations using vector similarity
matched_entities = vector_db_entities.similarity_search(' '.join(entities_to_search))
matched_relations = vector_db_relations.similarity_search(' '.join(relations))

print("Matched Entities: ", matched_entities)
print("Matched Relations: ", matched_relations)

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
            "content": f"You receive a question and some JSON, and you answer the question based on the information found in the JSON. You do not mention the JSON in the response, but just produce an answer.  Please use full IRIs, not preficed IRIs."
        },
        {
            "role": "user", 
            "content": f"Answer the question: {question} based on the following json: {json.dumps(all_documents)}",},
    ],
)

print("\n\nEXTRACTED & SUMMARIZED RESPONSES: \n")
print(response['choices'][0]['message']['content']) """
