import os
import pandas as pd
import re

from models.translator import detect_language
from models.rewriter import rewrite_instructions_with_quantity
from models.parser import (
    parse_ingredient_line,
    format_fraction,
    scale_cooking_time,
)

from math import log
from difflib import get_close_matches

BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
RECIPE_DATA_PATH = os.path.join(BASE_DIR, "data", "recipe_data.xlsx")
TRANSLATION_PATH = os.path.join(BASE_DIR, "data", "ingredients_translation.xlsx")

# Load all recipe sheets as dict: {sheet_name: DataFrame}
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

BASE_SERVINGS = 2

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
            except Exception:
                scaled = qty * (servings / base)  # fallback to linear
    else:
        scaled = qty * (servings / base)
    return {
        **item,
        "amount": round(scaled, 2),
        "formattedAmount": format_fraction(scaled) if scaled > 0 else ""
    }

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
        if not p["amount"] or p["amount"] == 0:
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
        "original_time": f"{original_time}",
        "adjusted_time": f"{adjusted_time} minutes",
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
