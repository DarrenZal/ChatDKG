import json
from urllib.parse import urlparse

def extract_base_url(url):
    """Extract the base URL from a full URL."""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/"
    else:
        return None

def infer_range_from_id(url, defined_entities):
    """Infer the range class from the entity URL."""
    if url in defined_entities:
        return defined_entities[url]
    return "owl:Thing"

def rdf_to_owl(file_paths, output_file):
    classes = set()
    properties = {}
    defined_entities = {}  # Keep track of defined entities and their types

    # First pass: Gather all defined entities with their types
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            json_data = json.load(file)
            assertions = json_data.get("assertion", [])
            for item in assertions:
                entity_id = item.get('@id')
                entity_types = item.get('@type', [])
                if entity_types:
                    for entity_type in entity_types:
                        defined_entities[entity_id] = entity_type.split('/')[-1]
                        classes.add(entity_type.split('/')[-1])

    # Second pass: Process properties
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            json_data = json.load(file)
            for item in json_data.get("assertion", []):
                for prop, values in item.items():
                    base_url = extract_base_url(prop)
                    property_name = prop.split('/')[-1]
                    if base_url and property_name:
                        if property_name not in properties:
                            properties[property_name] = {
                                'base_url': base_url,
                                'domains': set(),
                                'ranges': set()
                            }
                        entity_types = item.get('@type', [])
                        if entity_types:
                            properties[property_name]['domains'].update([t.split('/')[-1] for t in entity_types])
                        for value in values:
                            if isinstance(value, dict) and '@id' in value:
                                range_class = infer_range_from_id(value['@id'], defined_entities)
                                properties[property_name]['ranges'].add(range_class)

    # Writing the ontology
    with open(output_file, 'w') as file:
        file.write("@prefix schema: <http://schema.org/> .\n")
        file.write("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n")
        file.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
        file.write("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n")
        file.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n")

        # Writing classes and properties
        for class_type in classes:
            file.write(f"schema:{class_type} a owl:Class .\n")

        for property_name, prop_info in properties.items():
            file.write(f"schema:{property_name} a owl:ObjectProperty;\n")
            if prop_info['domains']:
                domains = ' '.join(f"schema:{domain}" for domain in prop_info['domains'])
                file.write(f"    rdfs:domain [ a owl:Class; owl:unionOf ({domains}) ] ;\n")
            if prop_info['ranges']:
                ranges = ' '.join(f"schema:{range}" for range in prop_info['ranges'])
                file.write(f"    rdfs:range [ a owl:Class; owl:unionOf ({ranges}) ] .\n\n")
            else:
                file.write(f"    rdfs:range owl:Thing .\n\n")

# List of RDF (JSON-LD) file paths
jsonld_files = ['did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181441.json', 
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181442.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181450.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181443.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181444.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181445.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181446.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181447.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181649.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181509.json',
                'did_dkg_otp_0x1a061136ed9f5ed69395f18961a0a535ef4b3e5f_1181448.json'] # Replace with your actual file paths
output_file_path = 'ontology.ttl'

# Convert RDF to OWL
rdf_to_owl(jsonld_files, output_file_path)
