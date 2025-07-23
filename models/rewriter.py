import re
import spacy

# Load English spaCy model. You can switch based on language if needed.
nlp = spacy.load("en_core_web_sm")

def build_ingredient_map(ingredients):
    """
    Create a dictionary mapping from normalized ingredient name to its updated text (e.g., '2 onions')
    """
    ing_map = {}
    for ing in ingredients:
        name = ing.get('ingredient', '').strip().lower()
        amt = ing.get('amount')
        unit = ing.get('unit', '').strip()

        # Format amount cleanly (e.g., show 0.5 as 1/2)
        formatted_amt = str(int(amt)) if amt == int(amt) else str(round(amt, 2))
        replacement = f"{formatted_amt} {unit} {name}".strip()
        ing_map[name] = replacement
    return ing_map

def rewrite_instruction(instruction, scaled_ingredients):
    """
    Rewrite a single instruction step by replacing ingredient names with scaled values
    """
    doc = nlp(instruction)
    ingredient_map = build_ingredient_map(scaled_ingredients)

    new_tokens = []
    for token in doc:
        word = token.text
        normalized = word.lower()
        if normalized in ingredient_map:
            new_tokens.append(ingredient_map[normalized])
        else:
            new_tokens.append(word)
    return ' '.join(new_tokens)
