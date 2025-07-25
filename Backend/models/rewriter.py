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
    full_text = ".\n".join(original_steps).strip()
    if not full_text.endswith(('.', '!', '?')):
        full_text += "."

    mentioned = set()
    skip_prefixes = ['for the', 'for garnishing', 'for seasoning']

    for ing in scaled_ingredients:
        if not ing.get("formattedAmount"):
            continue

        original_name = ing["name"].strip()
        core_name = extract_core_name(original_name)

        if core_name in mentioned:
            continue

        quantity_str = f"{ing['formattedAmount']}{' ' + ing['unit'] if ing['unit'] else ''}"

        full_phrase_pat = re.compile(rf"\b({re.escape(original_name)})\b", re.IGNORECASE | re.UNICODE)
        match = full_phrase_pat.search(full_text)
        if match:
            start_idx = match.start()
            preceding_text = full_text[max(0, start_idx - 20):start_idx].lower()
            if any(preceding_text.strip().endswith(p) for p in skip_prefixes):
                continue
            replacement = f"{quantity_str} {match.group(1)}"
            full_text = full_phrase_pat.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        word_pat = re.compile(rf"\b({re.escape(core_name)})\b", re.IGNORECASE | re.UNICODE)
        match = word_pat.search(full_text)
        if match:
            start_idx = match.start()
            preceding_text = full_text[max(0, start_idx - 20):start_idx].lower()
            if any(preceding_text.strip().endswith(p) for p in skip_prefixes):
                continue
            replacement = f"{quantity_str} {match.group(1)}"
            full_text = word_pat.sub(replacement, full_text, count=1)
            mentioned.add(core_name)
            continue

        doc = nlp(full_text)
        for chunk in doc.noun_chunks:
            if core_name in chunk.text.lower() and core_name not in mentioned:
                phrase_pat = re.compile(re.escape(chunk.text), re.IGNORECASE | re.UNICODE)
                replacement = f"{quantity_str} {chunk.text}"
                full_text = phrase_pat.sub(replacement, full_text, count=1)
                mentioned.add(core_name)
                break

    full_text = re.sub(r"\s{2,}", " ", full_text)
    full_text = re.sub(r"([.,])(?=[^\s])", r"\1 ", full_text)
    full_text = re.sub(r"(\w)([A-Z])", r"\1. \2", full_text)

    steps = [step.strip() for step in full_text.split(".\n") if step.strip()]
    steps = [step if step.endswith(".") else step + "." for step in steps]

    return steps
