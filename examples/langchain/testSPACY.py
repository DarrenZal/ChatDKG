import spacy
from dotenv import load_dotenv
load_dotenv()

nlp = spacy.blank("en")
llm = nlp.add_pipe("llm_textcat")
llm.add_label("INSULT")
llm.add_label("COMPLIMENT")
doc = nlp("You look ugly!")
print(doc.cats)