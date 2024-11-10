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

def extract_prefixes(json_data):
    """Extract prefixes from JSON-LD @context."""
    context = json_data.get("@context", {})
    prefixes = {}
    if isinstance(context, dict):
        for k, v in context.items():
            if isinstance(v, str):
                base_url = extract_base_url(v)
                if base_url:
                    prefixes[k] = base_url
    return prefixes

def resolve_full_uri(term, prefixes):
    """Resolve a prefixed term to its full URI using the given prefixes."""
    if ":" in term:
        prefix, local_id = term.split(':', 1)
        if prefix in prefixes:
            return prefixes[prefix] + local_id
        return term
    return term

def process_jsonld_data(json_data, defined_entities, all_prefixes, classes, properties):
    prefixes = extract_prefixes(json_data)
    all_prefixes.update(prefixes)

    if "@graph" in json_data:
        assertions = json_data["@graph"]
    elif "assertion" in json_data:
        assertions = json_data["assertion"]
    else:
        assertions = [json_data]

    if isinstance(assertions, dict):
        assertions = [assertions]

    for item in assertions:
        entity_id = item.get('@id')
        entity_types = item.get('@type', [])
        if not isinstance(entity_types, list):
            entity_types = [entity_types]
        if entity_types:
            for entity_type in entity_types:
                resolved_type = resolve_full_uri(entity_type, prefixes)
                defined_entities[entity_id] = resolved_type
                classes.add(resolved_type)

        for prop, values in item.items():
            if prop.startswith('@'):  # Skip JSON-LD reserved properties
                continue
            resolved_prop = resolve_full_uri(prop, all_prefixes)
            if resolved_prop not in properties:
                properties[resolved_prop] = {
                    'domains': set(),
                    'ranges': set()
                }
            if entity_types:
                for type_uri in entity_types:
                    properties[resolved_prop]['domains'].add(resolve_full_uri(type_uri, prefixes))
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if isinstance(value, dict) and '@id' in value:
                    range_class = infer_range_from_id(value['@id'], defined_entities)
                    properties[resolved_prop]['ranges'].add(range_class)

def rdf_to_owl(file_paths, output_file):
    classes = set()
    properties = {}
    defined_entities = {}  # Keep track of defined entities and their types
    all_prefixes = {}

    # Process JSON-LD data
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            json_data = json.load(file)
            process_jsonld_data(json_data, defined_entities, all_prefixes, classes, properties)

    # Generate dynamic prefixes for schemas
    schema_prefixes = {}
    schema_counter = 1
    for class_type in classes:
        prefix = extract_base_url(class_type)
        if prefix and prefix not in schema_prefixes:
            schema_prefixes[prefix] = f"schema{schema_counter}"
            schema_counter += 1

    for prop_uri in properties:
        prefix = extract_base_url(prop_uri)
        if prefix and prefix not in schema_prefixes:
            schema_prefixes[prefix] = f"schema{schema_counter}"
            schema_counter += 1

    # Writing the ontology with dynamic prefixes
    with open(output_file, 'w') as file:
        file.write("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n")  # Add the owl prefix
        file.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")  # Add the rdfs prefix
        for uri, schema_prefix in schema_prefixes.items():
            file.write(f"@prefix {schema_prefix}: <{uri}> .\n")
        file.write("\n")

        # Writing classes and properties
        for class_type in classes:
            prefix = extract_base_url(class_type)
            if prefix in schema_prefixes:
                local_name = class_type.replace(prefix, '')
                file.write(f"{schema_prefixes[prefix]}:{local_name} a owl:Class .\n")
            else:
                file.write(f"<{class_type}> a owl:Class .\n")

        for prop_uri, prop_info in properties.items():
            prefix = extract_base_url(prop_uri)
            if prefix in schema_prefixes:
                local_name = prop_uri.replace(prefix, '')
                file.write(f"{schema_prefixes[prefix]}:{local_name} a owl:ObjectProperty;\n")
            else:
                file.write(f"<{prop_uri}> a owl:ObjectProperty;\n")

            if prop_info['domains']:
                domains = ' '.join(f"{schema_prefixes[extract_base_url(domain)]}:{domain.replace(extract_base_url(domain), '')}" if extract_base_url(domain) in schema_prefixes else f"<{domain}>" for domain in prop_info['domains'])
                file.write(f"    rdfs:domain [ a owl:Class; owl:unionOf ({domains}) ] ;\n")
            if prop_info['ranges']:
                ranges = ' '.join(f"{schema_prefixes[extract_base_url(range)]}:{range.replace(extract_base_url(range), '')}" if extract_base_url(range) in schema_prefixes else f"<{range}>" for range in prop_info['ranges'])
                file.write(f"    rdfs:range [ a owl:Class; owl:unionOf ({ranges}) ] .\n")
            else:
                file.write("    rdfs:range owl:Thing .\n")
        file.write("\n")

# Convert RDF to OWL
jsonld_files = [
    'sampleRDF2.json',  # Replace 'path_to_your_file/' with the actual path to your files
    # Add more file paths as needed
]
output_file_path = 'ontology_output.ttl'
rdf_to_owl(jsonld_files, output_file_path)