import csv

def csv_to_tsv(csv_filename, tsv_filename):
    with open(csv_filename, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        
        with open(tsv_filename, mode='w', encoding='utf-8', newline='') as tsv_file:
            fieldnames = ['question', 'query']
            tsv_writer = csv.DictWriter(tsv_file, fieldnames=fieldnames, delimiter='\t')

            tsv_writer.writeheader()
            for row in csv_reader:
                tsv_writer.writerow({'question': row['question'], 'query': row['query']})

# Replace 'input.csv' with the path to your CSV file
csv_to_tsv('SPARQLqueries.csv', 'queries.tsv')