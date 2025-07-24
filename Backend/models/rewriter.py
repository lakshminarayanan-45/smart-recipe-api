import spacy

# Load English spaCy model once
nlp = spacy.load("en_core_web_sm")

def build_ingredient_map(ingredients):
    """
    Map ingredient name (lowercase) → replacement string like "1 1/2 cup sugar"
    """
    ing_map = {}
    for ing in ingredients:
        name = ing.get('name', '').strip().lower()
        amt = ing.get('formattedAmount', '')
        unit = ing.get('unit', '').strip()
        full_phrase = f"{amt} {unit} {name}".strip()
        ing_map[name] = full_phrase
    return ing_map

def rewrite_instruction(instruction, scaled_ingredients):
    """
    Replace ingredient names in instruction with scaled versions from ingredient map.
    """
    ingredient_map = build_ingredient_map(scaled_ingredients)
    doc = nlp(instruction)
    updated_tokens = []

    for token in doc:
        word = token.text
        normalized = word.lower()
        replaced = False

        # Exact match
        if normalized in ingredient_map:
            updated_tokens.append(ingredient_map[normalized])
            replaced = True
        else:
            # Fuzzy match for plurals or prefixes
            for ing_key in ingredient_map:
                if normalized.startswith(ing_key) or normalized.rstrip('s') == ing_key:
                    updated_tokens.append(ingredient_map[ing_key])
                    replaced = True
                    break
        if not replaced:
            updated_tokens.append(word)

    return ' '.join(updated_tokens)
