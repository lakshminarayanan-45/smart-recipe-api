import re
import spacy

# Load spaCy English model once
nlp = spacy.load("en_core_web_sm")

# Core name overrides for common ingredient name simplifications
CORE_NAME_OVERRIDES = {
    "கப் - தட்டையான அரிசி / அவல்": "அவல்",
    "கப் - வெல்லம்": "வெல்லம்",
    "கップ - துருவிய தேங்காய்": "தேங்காய்",
    "டேபிள் ஸ்பூன் - நெய்": "நெய்",
    "முந்திரி பருப்பு": "முந்திரி",
    "சிறிதளவு ஏலக்காய் தூள்.": "ஏலக்காய்",
    "गाजर - कद्दूकस की हुई": "गाजर",
    "कप पत्तागोभी - कद्दूकस की हुई": "पत्तागोभी",
    "छोटा चम्मच हल्दी": "हल्दी",
    "छोटा चम्मच सरसों के बीज": "सरसों",
    "छोटा चम्मच हींग": "हींग"
}

def extract_core_name(ingredient_name):
    """
    Extracts the core word/name of an ingredient for matching.
    Uses overrides or extracts last token from splitted name.
    """
    if ingredient_name in CORE_NAME_OVERRIDES:
        return CORE_NAME_OVERRIDES[ingredient_name]
    toks = re.split(r"[\s,\-\/\(\)]", ingredient_name)
    toks = [t.strip(".").strip() for t in toks if t.strip()]
    if toks:
        return toks[-1]
    return ingredient_name

def rewrite_instructions_with_quantity(original_steps, scaled_ingredients, servings):
    """
    Inject scaled quantities into the recipe instructions for each ingredient.

    Args:
        original_steps (list of str): List of original instruction sentences.
        scaled_ingredients (list of dict): List of ingredients with scaled amounts.
        servings (int): New number of servings (optional for future use).

    Returns:
        List of strings: rewritten instructions with scaled quantities injected.
    """
    # Join instructions text, ensuring sentence endings separated by ".\n"
    full_text = ".\n".join(original_steps).strip()

    # Make sure text ends with a period to separate sentences properly
    if not full_text.endswith(('.', '!', '?')):
        full_text += "."

    mentioned = set()  # Track which core ingredient names have been handled

    for ing in scaled_ingredients:
        original_name = ing['name'].strip()
        core_name = extract_core_name(original_name)

        if core_name in mentioned:
            continue  # Avoid multiple replacements for same core name

        quantity_str = f"{ing['formattedAmount']}{' ' + ing['unit'] if ing['unit'] else ''}"

        # Phase 1: Try full phrase exact match, case-insensitive with word boundaries
        full_phrase_pattern = re.compile(rf"\b({re.escape(original_name)})\b", re.IGNORECASE | re.UNICODE)
        match = full_phrase_pattern.search(full_text)
        if match:
            replacement = f"{quantity_str} {match.group(1)}"
            full_text = full_phrase_pattern.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        # Phase 2: Try matching core name as a word
        word_pattern = re.compile(rf"\b({re.escape(core_name)})\b", re.IGNORECASE | re.UNICODE)
        match = word_pattern.search(full_text)
        if match:
            replacement = f"{quantity_str} {match.group(1)}"
            full_text = word_pattern.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        # Phase 3: spaCy noun chunk match fallback - slower but more flexible
        doc = nlp(full_text)
        for chunk in doc.noun_chunks:
            if core_name in chunk.text.lower() and core_name not in mentioned:
                phrase_pattern = re.compile(re.escape(chunk.text), re.IGNORECASE | re.UNICODE)
                replacement = f"{quantity_str} {chunk.text}"
                full_text = phrase_pattern.sub(replacement, full_text, count=1)
                mentioned.add(core_name)
                break

    # Normalize spacing: replace multiple spaces with single space
    full_text = re.sub(r'\s{2,}', ' ', full_text)

    # Fix spacing after punctuation (add a space if missing after period or comma)
    full_text = re.sub(r'([.,])(?=[^\s])', r'\1 ', full_text)

    # Split instructions back into list, strip whitespace, ensure each ends with a period
    steps = [step.strip() for step in full_text.split(".\n") if step.strip()]
    steps = [step if step.endswith('.') else step + '.' for step in steps]

    return steps
