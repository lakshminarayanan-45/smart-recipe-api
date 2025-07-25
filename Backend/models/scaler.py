import os
import re
import pandas as pd
import spacy
from math import log
from fractions import Fraction
from difflib import get_close_matches
from models.translator import detect_language
from models.rewriter import rewrite_instructions_with_quantity
from models.parser import extract_amount_and_unit, parse_ingredient_line, format_fraction, scale_ingredient, scale_cooking_time

# Load spaCy only once in the module
nlp = spacy.load("en_core_web_sm")

# Excel data path (update this path according to your Backend/data folder)
BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
DATA_PATH = os.path.join(BASE_DIR, "data", "recipe_data.xlsx")
SCALE_TYPE_PATH = os.path.join(BASE_DIR, "data", "ingredient_scale_type.xlsx")  # Adjust if needed

# Read the recipe data Excel once at module load
xls = pd.ExcelFile(DATA_PATH, engine='openpyxl')

# Read the ingredient scale type lookup file once
scale_df = pd.read_excel(SCALE_TYPE_PATH, engine='openpyxl')

# Build scale lookup dict (ingredient name to scale_type)
SCALE_LOOKUP = {}
for _, row in scale_df.iterrows():
    scale_type = (
        row.get("Scale Type")
        or row.get("ScaleType")
        or row.get("scale_type")
    )
    if not scale_type:
        continue
    for col in scale_df.columns:
        if "name" in col.lower():
            ing_name = str(row[col]).strip().lower()
            if ing_name:
                SCALE_LOOKUP[ing_name] = scale_type.strip().upper()

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

BASE_SERVINGS = 2  # Base number of servings used for scaling calculations

def process_recipe_request(recipe_name: str, new_servings: int, translation_df: pd.DataFrame):
    # 1. Detect language and find corresponding sheet and row
    sheet_name, lang_col, lang_code, df_row = detect_language(xls, recipe_name)
    if df_row is None or df_row.empty:
        raise ValueError("Recipe not found.")

    row = df_row.iloc[0]

    # 2. Identify relevant columns
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

    # 3. Parse ingredients list from column string
    parsed_ingredients = parse_ingredient_line(str(row[ing_col]))

    # 4. Scale ingredients according to servings
    scaled_ingredients = [scale_ingredient(p, new_servings, BASE_SERVINGS) for p in parsed_ingredients]

    # 5. Extract and split instructions into list of steps
    original_steps = str(row[instr_col]).split(".\n")

    # 6. Rewrite instructions injecting scaled quantities
    rewritten_instructions = rewrite_instructions_with_quantity(original_steps, scaled_ingredients, new_servings)

    # 7. Return structured result matching prior output format
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
            }
            for ing in scaled_ingredients
        ],
        "steps": rewritten_instructions,
        "language_detected": lang_code
    }
