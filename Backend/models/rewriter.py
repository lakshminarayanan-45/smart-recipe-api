import re
import spacy

nlp = spacy.load("en_core_web_sm")

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
    full_text = ".\n".join(original_steps)
    mentioned = set()

    for ing in scaled_ingredients:
        original_name = ing['name'].strip()
        core_name = extract_core_name(original_name)

        if core_name in mentioned:
            continue

        replacement = f"{ing['formattedAmount']}{' ' + ing['unit'] if ing['unit'] else ''}"

        # Full phrase match
        full_phrase_pattern = re.compile(rf"\b({re.escape(original_name)})\b", re.IGNORECASE | re.UNICODE)
        match = full_phrase_pattern.search(full_text)
        if match:
            full_text = full_phrase_pattern.sub(f"{replacement} {match.group(1)}", full_text, count=1)
            mentioned.add(core_name)
            continue

        # Core word match
        word_pattern = re.compile(rf"\b({re.escape(core_name)})\b", re.IGNORECASE | re.UNICODE)
        match = word_pattern.search(full_text)
        if match:
            full_text = word_pattern.sub(f"{replacement} {match.group(1)}", full_text, count=1)
            mentioned.add(core_name)
            continue

        # spaCy noun chunk fallback
        doc = nlp(full_text)
        for chunk in doc.noun_chunks:
            if core_name in chunk.text.lower() and core_name not in mentioned:
                phrase_pattern = re.compile(re.escape(chunk.text), re.IGNORECASE | re.UNICODE)
                full_text = phrase_pattern.sub(f"{replacement} {chunk.text}", full_text, count=1)
                mentioned.add(core_name)
                break

    return full_text.split(".\n")
