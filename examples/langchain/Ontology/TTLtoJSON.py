import rdflib
import json

def convert_ttl_to_jsonld(ttl_path, jsonld_path):
    # Load the Turtle file into an RDFlib graph
    g = rdflib.Graph()
    g.parse(ttl_path, format="turtle")

    # Define a custom JSON-LD context with shorter aliases for common namespaces
    context = {
        "@context": {
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "schema": "http://schema.org/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        }
    }

    # Serialize the graph to JSON-LD using the custom context
    jsonld_data = g.serialize(format='json-ld', context=context, indent=4)
    jsonld_object = json.loads(jsonld_data)

    # Optionally, ensure that the output is wrapped under a single key if it helps with further processing
    wrapped_jsonld = {"@graph": jsonld_object} if isinstance(jsonld_object, list) else jsonld_object

    # Write the JSON-LD data to a file
    with open(jsonld_path, 'w') as jsonld_file:
        jsonld_file.write(json.dumps(wrapped_jsonld, indent=4))

# Specify the paths for the input Turtle file and the output JSON-LD file
ttl_path = 'ontology_output.ttl'
jsonld_path = 'ontology_output.jsonld'

# Convert the Turtle file to a JSON-LD file using aliases
convert_ttl_to_jsonld(ttl_path, jsonld_path)
