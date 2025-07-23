import re
import spacy

# Load English spaCy model. You can switch based on language.
nlp = spacy.load("en_core_web_sm")

def rewrite_instructions(instructions, ingredient_map):
    adjusted_steps = []
    for step in instructions:
        doc = nlp(step)
        new_tokens = []
        for token in doc:
            word = token.text
            normalized = word.lower()
            # Replace ingredient if it exists in our map
            if normalized in ingredient_map:
                new_tokens.append(str(ingredient_map[normalized]))
            else:
                new_tokens.append(word)
        adjusted_steps.append(' '.join(new_tokens))
    return adjusted_steps

