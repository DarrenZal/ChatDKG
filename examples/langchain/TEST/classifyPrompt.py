import os
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

def timed_function(func):
    """Decorator to measure execution time of a function."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time:.2f} seconds.")
        return result
    return wrapper

@timed_function
def classify_prompt(prompt, ontology_content):
    """Classify the prompt as either 'SPARQL' or 'RAG' using OpenAI's API."""

    client = OpenAI(api_key=os.getenv("OPENAI_KEY"))
    combined_prompt = f"{ontology_content}\n\n{prompt}"

    try:
        completion = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        temperature=0.2,
        messages=[
                {
                    "role": "system",
                    "content": "Classify the following prompt as either 'SPARQL' or 'RAG', where 'SPARQL' means that the prompt is a question that can be answered via a SPARQL query given an OWL ontology and the ID's of named entities, and 'RAG' means that the prompt is better answered by using retrieval augmented generation via passing data found via semantic similarity search to a LLM to provide a response."
                },
                {
                    "role": "user",
                    "content": combined_prompt
                }
            ]
        )

        classification = completion.choices[0].message.content.strip()
        completion_tokens = completion.usage.completion_tokens
        prompt_tokens = completion.usage.prompt_tokens
        total_tokens = completion.usage.total_tokens
        OpenAICallCost = 0.001*prompt_tokens/1000 + 0.002*completion_tokens/1000
        print(f"input tokens: {prompt_tokens}, output tokens: {completion_tokens}, cost: {OpenAICallCost}")
        return classification

    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return None

def read_ontology_file(file_path):
    """Reads the contents of an ontology file."""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return ""

if __name__ == "__main__":
    ontology_file_path = "ontology.ttl"
    ontology_content = read_ontology_file(ontology_file_path)
    prompt = "what is ReFi about?"
    result = classify_prompt(prompt, ontology_content)
    print(f"Classification Result: {result}")
