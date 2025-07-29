import os
import pandas as pd
import re
from math import log
from difflib import get_close_matches

# Adjust the import path or move detect_language in same file if needed
# Here, assume detect_language is in the same file for completeness.
# Or import it if you prefer it elsewhere.

# Assuming you put the detect_language here for self-containment:
def detect_language(all_sheets, recipe_name):
    LANGUAGE_SUFFIX = {
        "TamilName": "ta", "hindiName": "hn", "malayalamName": "kl",
        "kannadaName": "kn", "teluguName": "te", "frenchName": "french",
        "spanishName": "spanish", "germanName": "german"
    }
    for sheet_name, df in all_sheets.items():
        for lang_col in LANGUAGE_SUFFIX:
            if lang_col in df.columns:
                match = df[df[lang_col].astype(str).str.lower().str.strip() == recipe_name.lower()]
                if not match.empty:
                    return sheet_name, lang_col, LANGUAGE_SUFFIX[lang_col], match
        for col in ["name", "Name"]:
            if col in df.columns:
                match = df[df[col].astype(str).str.lower().str.strip() == recipe_name.lower()]
                if not match.empty:
                    return sheet_name, col, "en", match
    return None, None, None, None


BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
DATA_DIR = os.path.join(BASE_DIR, "data")
RECIPE_DATA_PATH = os.path.join(DATA_DIR, "Recipe App Dataset.xlsx")
TRANSLATION_PATH = os.path.join(DATA_DIR, "ingredients_translation.xlsx")

all_sheets = pd.read_excel(RECIPE_DATA_PATH, sheet_name=None, engine='openpyxl')
translation_df = pd.read_excel(TRANSLATION_PATH, engine='openpyxl')


def build_scale_lookup(df):
    scale_lookup = {}
    for _, row in df.iterrows():
        en_name = str(row.get('en', '')).strip().lower()
        scale_type = str(row.get('scale_type', 'LINEAR')).strip().upper()
        if en_name:
            scale_lookup[en_name] = scale_type
    return scale_lookup


SCALE_LOOKUP = build_scale_lookup(translation_df)
BASE_SERVINGS = 2


def get_scale_type(ingredient_name):
    norm = ingredient_name.lower()
    if norm in SCALE_LOOKUP:
        return SCALE_LOOKUP[norm]
    for key in SCALE_LOOKUP:
        if key in norm or norm in key:
            return SCALE_LOOKUP[key]
    tokens = re.split(r"[^\w]", norm)
    for t in tokens:
        if t in SCALE_LOOKUP:
            return SCALE_LOOKUP[t]
    matches = get_close_matches(norm, SCALE_LOOKUP.keys(), n=1, cutoff=0.75)
    if matches:
        return SCALE_LOOKUP[matches[0]]
    return "LINEAR"


def combine_names(original, translated):
    original_lower = original.lower()
    translated_lower = translated.lower()
    if translated_lower == original_lower:
        return original
    if translated_lower in original_lower:
        return original
    if original_lower in translated_lower:
        return translated
    original_tokens = original.split()
    translated_tokens = translated.split()
    combined = []
    for token in translated_tokens + original_tokens:
        if token.lower() not in [t.lower() for t in combined]:
            combined.append(token)
    return " ".join(combined)


def scale_ingredient(item, servings, base=BASE_SERVINGS):
    name = item["name"]
    qty = item["amount"]
    scale_type = get_scale_type(name)
    if scale_type == "FIXED":
        scaled = qty
    elif scale_type == "LOG":
        if servings <= 1:
            scaled = qty
        else:
            try:
                scaled = qty * (log(servings) / log(base))
            except (ValueError, ZeroDivisionError):
                scaled = qty * (servings / base)
    else:
        scaled = qty * (servings / base)
    return {
        **item,
        "amount": round(scaled, 2),
        "formattedAmount": format_fraction(scaled) if scaled > 0 else ""
    }


def format_fraction(x):
    # Format decimal numbers as fractions for user-friendly display (simple example)
    if abs(x - int(x)) < 1e-6:
        return str(int(x))
    from fractions import Fraction
    f = Fraction(x).limit_denominator(8)
    return f"{f.numerator}/{f.denominator}"


def scale_cooking_time(original_time, new_servings, base_servings):
    # Try to scale time linearly
    try:
        if isinstance(original_time, (int, float)):
            return round(original_time * new_servings / base_servings)
        # Try to parse time string containing digits, e.g. "20 minutes"
        import re
        m = re.search(r"(\d+)", str(original_time))
        if m:
            time_val = int(m.group(1))
            scaled_time = round(time_val * new_servings / base_servings)
            return f"{scaled_time} minutes"
        return original_time
    except Exception:
        return original_time


def parse_ingredient_line(text):
    items = [i.strip() for i in re.split(r",|\n", str(text)) if i.strip()]
    result = []
    for item in items:
        match = re.match(r"([\d\.\/]+)?\s*([a-zA-Z]+)?\s(.+)", item)
        if match:
            qty_text = match.group(1)
            try:
                amount = eval(qty_text) if qty_text else 1
            except Exception:
                amount = 1
            unit = match.group(2) if match.group(2) else ""
            name = match.group(3).strip()
            result.append({
                "amount": amount,
                "unit": unit.strip(),
                "name": name,
                "formattedAmount": format_fraction(amount) if amount > 0 else "",
            })
    return result


def rewrite_instructions_with_quantity(steps, scaled_ingredients, new_servings):
    # This should be your existing implementation or a simple placeholder.
    # Return steps unchanged for now:
    # (You can add logic to adjust quantities in instructions based on scaled ingredients.)
    return steps


def process_recipe_request(recipe_name: str, new_servings: int, translation_df: pd.DataFrame):
    sheet_name, lang_col, lang_code, df_row = detect_language(all_sheets, recipe_name)
    if df_row is None or df_row.empty:
        raise ValueError("Recipe not found.")

    row = df_row.iloc[0]

    ing_col = next((c for c in row.index if f"ingredients_{lang_code}" in c.lower()), None)
    if not ing_col:
        ing_col = next((c for c in row.index if "ingredients_en" in c.lower()), None)
    if not ing_col:
        raise ValueError("Ingredient column not found.")

    instr_col = next((c for c in row.index if f"instructions_{lang_code}" in c.lower()), None)
    if not instr_col:
        instr_col = next((c for c in row.index if "instructions_en" in c.lower()), None)
    if not instr_col:
        raise ValueError("Instruction column not found.")

    cook_col = next((c for c in row.index if c.lower() in ["cooking", "cookingtime"]), None)
    original_time = row[cook_col] if cook_col else "N/A"
    title = row[lang_col]
    adjusted_time = scale_cooking_time(original_time, new_servings, BASE_SERVINGS)

    parsed_ingredients = parse_ingredient_line(str(row[ing_col]))

    scaled_ingredients = []
    for p in parsed_ingredients:
        ingredient_name = p["name"]
        translated_name = ingredient_name
        if lang_code != "en" and lang_code in translation_df.columns:
            matches = translation_df[translation_df[lang_code].str.lower() == ingredient_name.lower()]
            if not matches.empty:
                translated_name = matches.iloc[0]['en']
        if p["amount"] is None:
            scaled = p.copy()
            scaled["formattedAmount"] = ""
        else:
            scaled = scale_ingredient(p, new_servings, BASE_SERVINGS)
        scaled["name"] = combine_names(ingredient_name, translated_name)
        scaled_ingredients.append(scaled)

    original_steps = str(row[instr_col]).split(".\n")
    rewritten_instructions = rewrite_instructions_with_quantity(original_steps, scaled_ingredients, new_servings)

    return {
        "recipe": title,
        "original_servings": BASE_SERVINGS,
        "new_servings": new_servings,
        "original_time": str(original_time),
        "adjusted_time": str(adjusted_time) if isinstance(adjusted_time, str) else f"{adjusted_time} minutes",
        "ingredients": [
            {
                "name": ing["name"],
                "formattedAmount": ing["formattedAmount"],
                "unit": ing.get("unit", ""),
            } for ing in scaled_ingredients
        ],
        "steps": rewritten_instructions,
        "language_detected": lang_code
    }
