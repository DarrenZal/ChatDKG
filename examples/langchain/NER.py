import spacy

# Load a larger model
nlp = spacy.load("en_core_web_md")  # or en_core_web_lg
doc = nlp("Who is Monty?")
for ent in doc.ents:
    print(ent.text, ent.start_char, ent.end_char, ent.label_)
