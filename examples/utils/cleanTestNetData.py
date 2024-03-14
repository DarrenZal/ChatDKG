from simplify_nested_ents import simplify_links_within_entities
from replace_string import replace_string_in_data
import json

# Load the JSON input data
with open('data2.json', 'r') as file:
    data = json.load(file)

# Apply the transformation to every list found at the top level in the data
for key, value in data.items():
    if isinstance(value, list):  # This assumes every list at the top level is a list of entities
        data[key] = [simplify_links_within_entities(entity) for entity in value]

# Replace URIs
old_base = "https://example.com"
new_base = "https://refidao.com"
data = replace_string_in_data(data, old_base, new_base)

old_base = "sameas"
new_base = "twitter"
data = replace_string_in_data(data, old_base, new_base)

def rename_sameas_attribute(entity):
    if 'sameas' in entity:
        new_keys = set()  # To handle the case where there are multiple URLs from different domains.
        for url in entity['sameas']:
            if 'twitter.com' in url:
                new_keys.add('twitter')
            elif 'linkedin.com' in url:
                new_keys.add('linkedin')
            # Add more conditions here for other domains if needed.
        
        for new_key in new_keys:
            # Initialize the new key list if it doesn't exist.
            if new_key not in entity:
                entity[new_key] = []
            
            # Move URLs to the new key based on domain.
            entity[new_key].extend([url for url in entity['sameas'] if new_key in url])
        
        del entity['sameas']  # Remove the original 'sameas' key after processing.
    return entity

def process_data_to_rename_attributes(data):
    if isinstance(data, dict):
        data = rename_sameas_attribute(data)  # Apply the renaming logic to the current dictionary.
        for key, value in data.items():
            data[key] = process_data_to_rename_attributes(value)  # Recursive call for nested dictionaries/lists.
    elif isinstance(data, list):
        return [process_data_to_rename_attributes(item) for item in data]  # Recursive call for each item in the list.
    return data

# Process the data to rename 'sameas' attributes
data = process_data_to_rename_attributes(data)

# Convert the modified data back to a JSON string for demonstration
json_output = json.dumps(data, indent=4, ensure_ascii=False)
print(json_output)


# Optionally, save the transformed JSON data back to a file
with open('transformed_data_new.json', 'w', encoding='utf-8') as f:
    f.write(json_output)