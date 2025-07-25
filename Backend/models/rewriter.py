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
    if ingredient_name in CORE_NAME_OVERRIDES:
        return CORE_NAME_OVERRIDES[ingredient_name]
    toks = re.split(r"[\s,\-\/\(\)]", ingredient_name)
    toks = [t.strip(".").strip() for t in toks if t.strip()]
    if toks:
        return toks[-1]
    return ingredient_name

def rewrite_instructions_with_quantity(original_steps, scaled_ingredients, servings):
    """
    Inject scaled quantities before ingredient names in recipe instructions,
    while avoiding injection before headers or non-ingredient phrases.

    Args:
        original_steps (list of str): List of original instruction sentences
        scaled_ingredients (list of dict): List with 'name', 'formattedAmount', 'unit' keys
        servings (int): Number of servings (currently unused, reserved for future)

    Returns:
        list of str: Rewritten instructions with quantities injected properly.
    """

    # Join instructions with proper sentence delimiter and ensure ending punctuation
    full_text = ".\n".join(original_steps).strip()
    if not full_text.endswith(('.', '!', '?')):
        full_text += "."

    mentioned = set()
    skip_prefixes = ['for the', 'for garnishing', 'for seasoning']

    for ing in scaled_ingredients:
        original_name = ing['name'].strip()
        core_name = extract_core_name(original_name)

        if core_name in mentioned:
            continue  # Avoid duplicate injection

        quantity_str = f"{ing['formattedAmount']}{' ' + ing['unit'] if ing['unit'] else ''}"

        # Phase 1: Full phrase exact match
        full_phrase_pattern = re.compile(
            rf"\b({re.escape(original_name)})\b", re.IGNORECASE | re.UNICODE)
        match = full_phrase_pattern.search(full_text)
        if match:
            # Check if preceding text contains a skip prefix indicating a header etc.
            start_idx = match.start()
            preceding_text = full_text[max(0, start_idx - 20):start_idx].lower()
            if any(preceding_text.strip().endswith(prefix) for prefix in skip_prefixes):
                continue  # skip injection near headings

            replacement = f"{quantity_str} {match.group(1)}"
            full_text = full_phrase_pattern.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        # Phase 2: Core word match
        word_pattern = re.compile(
            rf"\b({re.escape(core_name)})\b", re.IGNORECASE | re.UNICODE)
        match = word_pattern.search(full_text)
        if match:
            start_idx = match.start()
            preceding_text = full_text[max(0, start_idx - 20):start_idx].lower()
            if any(preceding_text.strip().endswith(prefix) for prefix in skip_prefixes):
                continue  # skip injecting (likely before a section header)

            replacement = f"{quantity_str} {match.group(1)}"
            full_text = word_pattern.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        # Phase 3: spaCy noun chunk fallback (slower but robust)
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

    # Fix spacing after punctuation if missing space
    full_text = re.sub(r'([.,])(?=[^\s])', r'\1 ', full_text)

    # Insert periods before uppercase letters that are missing punctuation (improves readability)
    full_text = re.sub(r'(\w)([A-Z])', r'\1. \2', full_text)

    # Split back into list of steps, stripping whitespace
    steps = [step.strip() for step in full_text.split(".\n") if step.strip()]
    # Append period if missing at end of step
    steps = [step if step.endswith('.') else step + '.' for step in steps]

    return steps
