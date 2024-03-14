import os
import json
from dotenv import load_dotenv
from pyairtable import Api

# Load environment variables from .env file
load_dotenv()


# Now you can safely access the environment variable
api_key = os.getenv('AIRTABLE_API_KEY')
if api_key is None:
    raise ValueError("Missing AIRTABLE_API_KEY in environment variables.")

# Assuming you have the base ID and table name correctly set
base_id = os.getenv('BASE_ID') # Replace this with your actual base ID

api = Api(api_key)

""" filename = 'organizations.json'
table_name = "organizations"  # The name of your table
table = api.table(base_id, table_name)
data = table.all()
# Write the data to
# Write the data to a JSON file
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
print(f"Data written to {filename}") """

""" filename = 'people.json'
table_name = "people"  # The name of your table
table = api.table(base_id, table_name)
data = table.all()
# Write the data to a JSON file
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
print(f"Data written to {filename}") """


filename = 'deals.json'
table_name = "people"  # The name of your table
base = api.base("appouTuCgLMpfOTOa")
schema = base.schema().tables


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        # Check if the object is an instance of a custom class by checking for a __dict__ attribute
        if hasattr(obj, '__dict__'):
            # Serialize using the object's dictionary representation
            return obj.__dict__
        # For other types (like lists of objects), let the base class handle them
        return super(CustomEncoder, self).default(obj)

# Assuming 'schema' is the variable that holds your list of TableSchema objects
filename = 'deals.json'
with open(filename, 'w', encoding='utf-8') as f:
    # Directly serialize 'schema' using the custom encoder without manually converting objects to dictionaries
    json.dump(schema, f, cls=CustomEncoder, ensure_ascii=False, indent=4)

print(f"Data written to {filename}")