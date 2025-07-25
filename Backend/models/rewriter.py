import re
import spacy

# Load spaCy model once
nlp = spacy.load("en_core_web_sm")

# Overrides for core ingredient names (customize as needed)
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
    # Join instructions preserving sentence endings with ".\n"
    full_text = ".\n".join(original_steps).strip()

    # Ensure the text ends with a period to avoid accidental sentence concatenation
    if not full_text.endswith(('.', '!', '?')):
        full_text += "."

    mentioned = set()

    for ing in scaled_ingredients:
        original_name = ing['name'].strip()
        core_name = extract_core_name(original_name)

        if core_name in mentioned:
            continue

        quantity_str = f"{ing['formattedAmount']}{' ' + ing['unit'] if ing['unit'] else ''}"

        # Phase 1: full phrase match with word boundaries
        full_phrase_pattern = re.compile(rf"\b({re.escape(original_name)})\b", re.IGNORECASE | re.UNICODE)
        match = full_phrase_pattern.search(full_text)
        if match:
            replacement = f"{quantity_str} {match.group(1)}"
            full_text = full_phrase_pattern.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        # Phase 2: core word match
        word_pattern = re.compile(rf"\b({re.escape(core_name)})\b", re.IGNORECASE | re.UNICODE)
        match = word_pattern.search(full_text)
        if match:
            replacement = f"{quantity_str} {match.group(1)}"
            full_text = word_pattern.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        # Phase 3: spaCy noun chunk fallback match
        doc = nlp(full_text)
        for chunk in doc.noun_chunks:
            if core_name in chunk.text.lower() and core_name not in mentioned:
                phrase_pattern = re.compile(re.escape(chunk.text), re.IGNORECASE | re.UNICODE)
                replacement = f"{quantity_str} {chunk.text}"
                full_text = phrase_pattern.sub(replacement, full_text, count=1)
                mentioned.add(core_name)
                break

    # Normalize multiple spaces
    full_text = re.sub(r'\s{2,}', ' ', full_text)

    # Fix spacing with punctuation: ensure one space after commas/periods if missing
    full_text = re.sub(r'([.,])(?=[^\s])', r'\1 ', full_text)

    # Split back into steps using ".\n", strip each step and ensure period at end
    steps = [step.strip() for step in full_text.split(".\n") if step.strip()]
    steps = [step if step.endswith('.') else step + '.' for step in steps]

    return steps
