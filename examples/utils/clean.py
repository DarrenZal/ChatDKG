import json
import re

def strip_text_fields(data):
    """
    Recursively strips leading and trailing spaces from all string fields in the JSON data.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = strip_text_fields(value)  # Apply recursively to each value
    elif isinstance(data, list):
        return [strip_text_fields(item) for item in data]  # Apply recursively to each item in the list
    elif isinstance(data, str):
        return data.strip()  # Strip spaces from string values
    return data

def remove_emojis(text):
    if not isinstance(text, str):
        return text
    
    emoji_pattern = re.compile(
        "["
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbat symbols
        "\U00002B50-\U00002B59"  # Additional stars
        "\U00002600-\U000026FF"  # Miscellaneous Symbols
        "\U0001F980-\U0001F984"  # Additional animal symbols
        "\U0001F9C0"             # Cheese wedge
        "]+",
        flags=re.UNICODE,
    )
    cleaned_text = emoji_pattern.sub(r"", text)
    return cleaned_text.strip()  # Trim leading and trailing spaces

def remove_variation_selector(text):
    if not isinstance(text, str):
        return text

    # Directly replace the Variation Selector-16 with an empty string
    # This targets the specific issue with lingering U+FE0F characters
    text = text.replace('\uFE0F', '')

    return text

def process_fields(value):
    """Process string or list of strings to remove emojis and variation selectors."""
    if isinstance(value, str):  # If value is a string, remove emojis and variation selectors
        cleaned_value = remove_emojis(value)
        cleaned_value = remove_invisible_characters(cleaned_value)
        cleaned_value = remove_variation_selector(cleaned_value)
        return cleaned_value
    elif isinstance(value, list):  # If value is a list, check each item
        return [process_fields(item) for item in value]
    return value

def remove_invisible_characters(text):
    if not isinstance(text, str):
        return text

    # Encode the text to UTF-8 to handle Unicode characters correctly
    text_utf8 = text.encode('utf-8')

    # Pattern to match invisible characters including Variation Selector-16 (U+FE0F)
    # encoded as UTF-8. This direct approach uses the UTF-8 encoded representation
    # of the characters to ensure they are correctly identified and removed.
    invisible_char_utf8_pattern = re.compile(
        b"("  
        b"\xe2\x80\x8b|\xe2\x80\x8c|\xe2\x80\x8d"  # Zero width space, joiner, non-joiner
        b"|\xef\xb8\x8f"  # Variation Selector-16
        b"|\xe2\x81\xa0"  # Word Joiner
        b"|\xe1\xa0\x8e"  # Mongolian Vowel Separator
        b"|\xc2\xad"      # Soft Hyphen
        b"|\xe2\x81\xa1|\xe2\x81\xa2|\xe2\x81\xa3|\xe2\x81\xa4"  # Function Application, Invisible Times, etc.
        b")+" 
    )
    cleaned_text_utf8 = invisible_char_utf8_pattern.sub(b"", text_utf8)

    # Decode the cleaned UTF-8 text back to a Python string
    cleaned_text = cleaned_text_utf8.decode('utf-8')

    return cleaned_text


def process_organizations(input_filename, output_filename):
    # Read the input file directly to avoid manipulating the JSON string
    with open(input_filename, 'r', encoding='utf-8') as file:
        data = json.load(file)

    for entry in data:
        if 'fields' in entry:
            for key, value in entry['fields'].items():
                entry['fields'][key] = process_fields(value)

    # Remove the 'Logo' attribute from each entry
    for entry in data:
        if 'fields' in entry and 'Logo' in entry['fields']:
            del entry['fields']['Logo']


    data = strip_text_fields(data)

    # Write the modified data to the output file
    with open(output_filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Call the function to process the JSON file
process_organizations('organizations.json', 'organizations_cleaned.json')
