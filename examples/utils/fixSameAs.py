import json
import re

# Helper function to validate URL
def is_valid_url(url):
    return url.startswith('http://') or url.startswith('https://')

def convert_to_url(obj):
    # Check and modify 'isBasedOn' if present
    if 'isBasedOn' in obj:
        if isinstance(obj['isBasedOn'], str):
            obj['isBasedOn'] = "https://" + obj['isBasedOn'].replace(" ", "")
        else:
            # Handle the case where 'isBasedOn' is not a string
            print(obj['isBasedOn'], "is not a string for 'isBasedOn'")

    # Check and modify 'isPartOf' if present
    if 'isPartOf' in obj:
        if isinstance(obj['isPartOf'], str):
            obj['isPartOf'] = "https://" + obj['isPartOf'].replace(" ", "")
        else:
            # Handle the case where 'isPartOf' is not a string
            print(obj['isPartOf'], "is not a string for 'isPartOf'")

# Function to extract and validate URLs from strings
def extract_and_validate_url(item, key):
    if key in item:
        url_match = re.search(r'\((https?://[^\s]+)\)', item[key])
        if url_match:
            item[key] = url_match.group(1)
        else:
            del item[key]  # Remove the key if the URL is not valid

# Sanitize '@id' and 'logo' fields
def sanitize_field(obj, field_name):
    if field_name in obj:
        if field_name == 'logo':
            # Extract URL from 'logo' string
            url = extract_and_validate_url(obj[field_name])
        else:
            url = obj[field_name]
        
        # If URL is invalid or not present, delete the key
        if not url or not is_valid_url(url):
            del obj[field_name]
        else:
            obj[field_name] = url

# Sanitize 'name' attribute by removing extra quotes
def sanitize_name(name_value):
    return name_value.replace('\"\"', '\"').strip()

# Recursive function to walk through the JSON and clean logo attributes
def sanitize_json(obj):
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if key == 'logo':
                extract_and_validate_url(obj, key)
            elif key == '@id' or key == 'url':
                sanitize_field(obj, key)
            elif key == 'name':
                obj[key] = sanitize_name(value)
            else:
                sanitize_json(value)
    elif isinstance(obj, list):
        for item in obj:
            sanitize_json(item)

# Helper function to validate URL
def is_valid_url(url):
    return url.startswith('http://') or url.startswith('https://')

# Regular expression to find URL in parentheses
def extract_url_from_image(image_string):
    match = re.search(r'\((https?://[^\s]+)\)', image_string)
    return match.group(1) if match else None

def extract_and_validate_url(key, item):
    if key in item:
        url = extract_url_from_image(item[key])
        # If URL is invalid or not present, delete the key
        if not url or not is_valid_url(url):
            del item[key]
        else:
            item[key] = url

# Define your base URI
BASE_URI = "https://example.com/"

# Modify the sanitize_id function to prepend the base URI only if not a valid URL
def sanitize_id(id_value):
    # If the ID is already a valid URL, return it as is
    if is_valid_url(id_value):
        return id_value

    # Replace all whitespace characters with a hyphen
    sanitized_id = re.sub(r'\s+', '-', id_value)
    # Replace em dash and en dash with a hyphen
    sanitized_id = re.sub(r'[—–]', '-', sanitized_id)
    # Remove all characters that are not valid in a URI (alphanumeric, hyphen, period, underscore, or colon)
    sanitized_id = re.sub(r'[^a-zA-Z0-9\-\._:]', '', sanitized_id)
    # Prepend the base URI
    return BASE_URI + sanitized_id

# Sanitize 'name' attribute by removing extra quotes
def sanitize_name(name_value):
    return name_value.replace('\"\"', '\"').strip()

# Function to remove "type" attributes
def remove_type_attributes(obj):
    if isinstance(obj, dict):
        keys_to_remove = [key for key in obj if key.lower() == "type" and key != "@type"]
        for key in keys_to_remove:
            del obj[key]
        for key, value in list(obj.items()):
            remove_type_attributes(value)
    elif isinstance(obj, list):
        for item in obj:
            remove_type_attributes(item)

data = []

# Load JSON-LD data
with open('../utils/combined_data.json', 'r') as file:
    data = json.load(file)

# Go through each key in the JSON data
for key, entries in data.items():
    if isinstance(entries, list):
        for item in entries:
            if '@id' in item:
                original_id = item['@id']
                sanitized_id = sanitize_id(original_id)
                item['@id'] = sanitized_id
            if 'sameAs' in item:
                # Split the 'sameAs' string into individual URLs, filter out any empty strings
                item['sameAs'] = [url.strip() for url in item['sameAs'][0].split(',') if url.strip()]
                # Validate the URLs and filter out any that are not valid
                item['sameAs'] = [url for url in item['sameAs'] if is_valid_url(url)]

def sanitize_type(type_value):
    # Remove emoji and any other non-standard characters for a type
    sanitized_type = re.sub(r'[^\w\s/]', '', type_value)
    # Optionally, map to a valid URI or term defined in @context
    # sanitized_type = type_mapping.get(sanitized_type, sanitized_type)
    return sanitized_type.strip()

def sanitize_field(obj, field_name):
    if field_name in obj:
        if isinstance(obj[field_name], str):
            url_match = re.search(r'\((https?://[^\s]+)\)', obj[field_name])
            if url_match:
                obj[field_name] = url_match.group(1)
            else:
                del obj[field_name]  # Remove the key if the URL is not valid


def rename_and_sanitize_keys(obj, old_key, new_key):
    """
    Recursively go through the object and replace keys that match old_key with new_key.
    Also sanitize '@id' and 'logo' fields at any level of nesting.
    """
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            new_obj_key = new_key if key == old_key else key
            if new_obj_key == '@id' or new_obj_key == 'logo':
                sanitize_field(obj, new_obj_key)
            else:
                obj[new_obj_key] = rename_and_sanitize_keys(obj.pop(key), old_key, new_key)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            obj[index] = rename_and_sanitize_keys(item, old_key, new_key)
    return obj

def sanitize_jsonld_data(obj):
    """
    Recursively go through the object and sanitize '@id' and '@url' fields,
    remove '@url' entries, and perform other sanitization as needed.
    """
    if isinstance(obj, dict):
        keys_to_delete = []
        for key, value in obj.items():
            if key == '@id':
                obj[key] = sanitize_id(value)
            elif key == 'isBasedOn':  # Add this condition
                convert_to_url(obj)
            elif key == 'isPartOf':  # Add this condition
                convert_to_url(obj)
            elif key == 'url':  # Check for 'url' attribute and mark it for deletion
                keys_to_delete.append(key)
            elif key == 'name':
                obj[key] = sanitize_name(value)
            elif key == '@type':
                obj[key] = sanitize_type(value)
                
            # Recursively sanitize nested dictionaries and lists
            else:
                obj[key] = sanitize_jsonld_data(value)
        # Delete keys that were marked for deletion including 'url'
        for key in keys_to_delete:
            del obj[key]
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            obj[index] = sanitize_jsonld_data(item)
    return obj

# Rename all 'Local Community' keys to 'LocalCommunity'
data = rename_and_sanitize_keys(data, 'Local Community', 'LocalCommunity')

data = sanitize_jsonld_data(data)

remove_type_attributes(data)

# Go through each key in the JSON data
for key, entries in data.items():
    if isinstance(entries, list):
        for item in entries:
            if '@id' in item:
                original_id = item['@id']
                sanitized_id = sanitize_id(original_id)
                item['@id'] = sanitized_id
            if 'sameAs' in item:
                filtered_urls = [url for url in item['sameAs'] if is_valid_url(url)]
                if filtered_urls:
                    item['sameAs'] = filtered_urls
                else:
                    del item['sameAs']
            if 'image' in item:
                url = extract_url_from_image(item['image'])
                # If URL is invalid or not present, delete the 'image' key
                if not url or not is_valid_url(url):
                    del item['image']
                else:
                    item['image'] = url
            if 'logo' in item:
                url = extract_url_from_image(item['logo'])
                # If URL is invalid or not present, delete the 'image' key
                if not url or not is_valid_url(url):
                    del item['logo']
                else:
                    item['logo'] = url
            if 'name' in item:
                item['name'] = sanitize_name(item['name'])
            if '@type' in item:
                item['@type'] = sanitize_type(item['@type'])

# Save the cleaned JSON-LD data back to the file
with open('../utils/combined_data_cleaned.json', 'w') as file:
    json.dump(data, file, indent=4)

print("Cleanup complete. Invalid '@id' entries have been sanitized, non-URL 'sameAs' entries and non-standard 'image' entries have been removed or corrected. 'name' attributes have been cleaned, and 'Local Community' has been corrected to 'LocalCommunity'.")
