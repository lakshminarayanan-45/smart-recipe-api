import re
import spacy

# Load spaCy model once
nlp = spacy.load("en_core_web_sm")

# Core name overrides for ingredient name simplifications (customize as needed)
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
    Extract core word from ingredient name for matching.
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
    Inject scaled ingredient quantities into recipe instructions.

    Args:
        original_steps (list[str]): list of instruction sentences.
        scaled_ingredients (list[dict]): list of ingredients with keys 'name', 'formattedAmount', 'unit'.
        servings (int): number of servings (not used currently).

    Returns:
        list[str]: list of instructions with quantities injected.
    """

    # Join instructions preserving sentence boundaries
    full_text = ".\n".join(original_steps).strip()
    if not full_text.endswith(('.', '!', '?')):
        full_text += "."

    mentioned = set()
    skip_prefixes = ['for the', 'for garnishing', 'for seasoning']

    for ing in scaled_ingredients:
        original_name = ing['name'].strip()
        core_name = extract_core_name(original_name)

        if core_name in mentioned:
            continue  # avoid duplicate injection

        quantity_str = f"{ing['formattedAmount']}{' ' + ing['unit'] if ing['unit'] else ''}"

        # Phase 1: full phrase exact match
        full_phrase_pattern = re.compile(
            rf"\b({re.escape(original_name)})\b", re.IGNORECASE | re.UNICODE)
        match = full_phrase_pattern.search(full_text)
        if match:
            start_idx = match.start()
            preceding_text = full_text[max(0, start_idx - 20):start_idx].lower()
            if any(preceding_text.strip().endswith(prefix) for prefix in skip_prefixes):
                continue  # skip injecting before section headers

            replacement = f"{quantity_str} {match.group(1)}"
            full_text = full_phrase_pattern.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        # Phase 2: core word exact match
        word_pattern = re.compile(
            rf"\b({re.escape(core_name)})\b", re.IGNORECASE | re.UNICODE)
        match = word_pattern.search(full_text)
        if match:
            start_idx = match.start()
            preceding_text = full_text[max(0, start_idx - 20):start_idx].lower()
            if any(preceding_text.strip().endswith(prefix) for prefix in skip_prefixes):
                continue

            replacement = f"{quantity_str} {match.group(1)}"
            full_text = word_pattern.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        # Phase 3: spaCy noun chunk fallback
        doc = nlp(full_text)
        for chunk in doc.noun_chunks:
            if core_name in chunk.text.lower() and core_name not in mentioned:
                phrase_pattern = re.compile(re.escape(chunk.text), re.IGNORECASE | re.UNICODE)
                replacement = f"{quantity_str} {chunk.text}"
                full_text = phrase_pattern.sub(replacement, full_text, count=1)
                mentioned.add(core_name)
                break

    # Clean up spaces
    full_text = re.sub(r'\s{2,}', ' ', full_text)

    # Ensure there's a space after punctuation marks
    full_text = re.sub(r'([.,])(?=[^\s])', r'\1 ', full_text)

    # Insert period before uppercase letter if missing between sentences
    full_text = re.sub(r'(\w)([A-Z])', r'\1. \2', full_text)

    # Split back into instructions
    steps = [step.strip() for step in full_text.split(".\n") if step.strip()]

    # Ensure each step ends with a period
    steps = [step if step.endswith('.') else step + '.' for step in steps]

    return steps
