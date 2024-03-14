def replace_string_in_data(data, old_uri, new_uri):
    """
    Recursively replaces all occurrences of old_str with new_str in the provided data.

    Parameters:
    - data: The data structure (dict, list, str) to modify.
    - old_str (str): The string to replace.
    - new_str (str): The new string to use.

    Returns:
    - The modified data with all URIs replaced.
    """
    if isinstance(data, dict):
        return {k: replace_string_in_data(v, old_uri, new_uri) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_string_in_data(item, old_uri, new_uri) for item in data]
    elif isinstance(data, str):
        return data.replace(old_uri, new_uri)
    else:
        return data  # Return the data unchanged if it's not a dict, list, or str.