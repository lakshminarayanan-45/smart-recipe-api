import re
import spacy

# Load English spaCy model
nlp = spacy.load("en_core_web_sm")

def build_ingredient_map(ingredients):
    """
    Create a dictionary mapping normalized ingredient name → replacement string (e.g., '2 tbsp sugar')
    """
    ing_map = {}
    for ing in ingredients:
        name = ing.get('ingredient', '').strip().lower()
        amt = ing.get('amount', 0)
        unit = ing.get('unit', '').strip()

        # Format amount nicely (e.g., 0.5 → 1/2, 1.25 → 1 1/4)
        if amt == int(amt):
            formatted_amt = str(int(amt))
        else:
            formatted_amt = str(round(amt, 2))

        full_phrase = f"{formatted_amt} {unit} {name}".strip()
        ing_map[name] = full_phrase
    return ing_map

def rewrite_instruction(instruction, scaled_ingredients):
    """
    Rewrite a single instruction by replacing ingredient names with scaled versions.
    """
    doc = nlp(instruction)
    ingredient_map = build_ingredient_map(scaled_ingredients)

    updated_tokens = []
    for token in doc:
        word = token.text
        normalized = word.lower()

        # Try exact match
        if normalized in ingredient_map:
            updated_tokens.append(ingredient_map[normalized])
        else:
            # Try fuzzy match: e.g., if "onions" in sentence, match "onion"
            matched = False
            for ing_key in ingredient_map:
                if normalized.startswith(ing_key) or normalized.rstrip('s') == ing_key:
                    updated_tokens.append(ingredient_map[ing_key])
                    matched = True
                    break
            if not matched:
                updated_tokens.append(word)

    return ' '.join(updated_tokens)
