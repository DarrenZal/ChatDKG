### Overview

This code handles Embeddings related functionality.  Text embeddings are created with LLMs and can be stored in a vector db for similarity search for RAG.

### Contents
entityEmbeddingSuggestion.js: takes an Ontology ttl file as input.  Makes a file with suggested feastures to embed for each entity type.  Outputs file suggestedEntityEmbeddings.json.


generateEntityEmbeddingsMainnet.js: takes suggestedEntityEmbeddings.json and creates the embeddings based on what fields should be embedded for each entity type.  Outputs entitiesMainnet.tsv.

queriesMainnet.tsv: This is a manually created file with sets of natural language questions and their SPARQL coutnerparts.  This is a way to manually embed natural language questions for similarity search with prompts, and for which the SPARQL query can be retrieved.

uploadEmbeddingsMainnet.py: uploads entity embeddings to vector db

uploadQueriesMainnet.py: uploads query embeddings to vector db

### Usage

First make sure that an ontology file exists at "../Ontology/ontology.ttl".  Note, there is a helper function in that folder KnowledgeAssetsToOWL.py which takes the UAL's of knowledge assets and creates a ontology.ttl file based on the data.

To generate suggestedEntityEmbeddings.json:
```node entityEmbeddingSuggestion.js```

To generate entitiesMainnet.tsv:
```node generateEntityEmbeddingsMainnet.js```

To upload entity embeddings:
```python uploadEmbeddingsMainnet.py```

To upload queries:
```python uploadQueriesMainnet.py```