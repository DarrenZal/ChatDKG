#For link attributes of entities, This will remove all extra fields other than the id

import json

def simplify_links_within_entities(entity):
    if isinstance(entity, dict):
        # Iterates through dictionary items
        for key, value in list(entity.items()):
            # Check if value is a dictionary containing '@id' and simplify it, if necessary
            if isinstance(value, dict) and '@id' in value and len(value) > 1:
                entity[key] = {'@id': value['@id']}
            # Recurse if value is a list or dictionary but not a simple '@id' dictionary
            elif isinstance(value, (list, dict)):
                entity[key] = simplify_links_within_entities(value)
    elif isinstance(entity, list):
        # Process each item in the list
        new_list = []
        for item in entity:
            # Simplify item if it's a dictionary containing '@id' with more attributes
            if isinstance(item, dict) and '@id' in item and len(item) > 1:
                new_list.append({'@id': item['@id']})
            # Recurse for item if it's a list or a dictionary
            else:
                new_list.append(simplify_links_within_entities(item))
        return new_list
    # Base case: return the entity as it is if it's neither a dictionary nor a list
    return entity


