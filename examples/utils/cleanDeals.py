import json
import re

# Add your existing functions here: strip_text_fields, remove_emojis, etc.

def process_data(input_filename, output_filename):
    with open(input_filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Assuming the structure is a dict with keys pointing to lists
    if 'deals_json_ld' in data and isinstance(data['deals_json_ld'], list):
        # Now we have the list, we can process it
        formatted_data = format_amount_investments(data['deals_json_ld'])
        # For demonstration, we'll just focus on deals_json_ld
        # You would repeat similar processing for other sections as needed
        data['deals_json_ld'] = formatted_data

    # Write the potentially modified data back to the output file
    with open(output_filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Adjust this function to work directly on the list of deals
def format_amount_investments(deals):
    for deal in deals:
        if deal.get('@type') == 'InvestmentOrGrant' and 'amount' in deal and not isinstance(deal['amount'], dict):
            deal['amount'] = {
                "@value": str(deal['amount']),
                "@type": "http://www.w3.org/2001/XMLSchema#decimal"
            }
    return deals

# Adjust filenames as necessary
process_data('transformed_data_new.json', 'transformed_data_new_deals_cleaned.json')


