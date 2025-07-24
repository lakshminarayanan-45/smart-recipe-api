import os
import pandas as pd
from models.translator import detect_and_translate
from models.rewriter import rewrite_instruction
from models.parser import extract_amount_and_unit

# Compute base directory: one level up from models/ is Backend/
BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
DATA_PATH = os.path.join(BASE_DIR, "data", "recipe_data.xlsx")

def process_recipe_request(recipe_name: str, new_servings: int, translation_df: pd.DataFrame):
    # Load Excel recipe data
    xls = pd.ExcelFile(DATA_PATH)
    recipes_df = xls.parse("recipes")
    ingredients_df = xls.parse("ingredients")
    instructions_df = xls.parse("instructions")

    # Filter recipe
    recipe_row = recipes_df[recipes_df['name'].str.lower() == recipe_name.lower()]
    if recipe_row.empty:
        raise ValueError("Recipe not found.")

    original_servings = int(recipe_row.iloc[0]['servings'])
    original_cook_time = int(recipe_row.iloc[0]['cook_time'])

    # Determine language column (non-standardize exclusion)
    language_cols = [col for col in ingredients_df.columns if col.lower() not in ['recipe_name', 'amount', 'unit']]
    if not language_cols:
        raise ValueError("No language column found in ingredients data.")
    language_column = language_cols[-1]

    # Detect language from first ingredient or default to 'en' if empty
    first_ing = ingredients_df[language_column].iloc[0]
    if not isinstance(first_ing, str) or not first_ing.strip():
        lang = 'en'
    else:
        lang = detect_and_translate(first_ing, detect_only=True).lower()

    # Filter ingredients and instructions for the recipe
    recipe_ingredients = ingredients_df[ingredients_df['recipe_name'].str.lower() == recipe_name.lower()]
    recipe_steps = instructions_df[instructions_df['recipe_name'].str.lower() == recipe_name.lower()]

    # Process ingredients (scale and translate)
    scaled_ingredients = []
    for _, row in recipe_ingredients.iterrows():
        ing_name_local = row[language_column]
        unit = row.get('unit', '') or ''
        raw_amt = row.get('amount', '') or ''

        parsed_amt, _ = extract_amount_and_unit(str(raw_amt))
        scaled_amt = parsed_amt * new_servings / original_servings

        translated_name = ing_name_local
        if lang != "en":
            # Use translation_df to map translated name
            matches = translation_df[translation_df[lang].str.lower() == str(ing_name_local).lower()]
            if not matches.empty:
                translated_name = matches.iloc[0]['en']

        scaled_ingredients.append({
            "name": translated_name,
            "formattedAmount": format_fraction(scaled_amt),
            "unit": unit
        })

    # Adjust cook time heuristically
    est_cook_time = int(original_cook_time + 0.1 * (new_servings - original_servings) * original_cook_time)

    # Rewrite instructions with scaled ingredients
    updated_instructions = []
    for _, row in recipe_steps.iterrows():
        original_step = row[language_column]
        rewritten = rewrite_instruction(original_step, scaled_ingredients)
        updated_instructions.append(rewritten)

    return {
        "recipe": recipe_name,
        "original_servings": original_servings,
        "new_servings": new_servings,
        "original_time": f"{original_cook_time} minutes",
        "adjusted_time": f"{est_cook_time} minutes",
        "ingredients": scaled_ingredients,
        "steps": updated_instructions,
        "language_detected": lang
    }

def format_fraction(amount: float) -> str:
    """Format float to fractions, e.g., 1 1/2, 3/4."""
    from fractions import Fraction
    frac = Fraction(amount).limit_denominator(8)
    if frac.numerator == 0:
        return "0"
    elif frac.numerator < frac.denominator:
        return f"{frac.numerator}/{frac.denominator}"
    elif frac.numerator % frac.denominator == 0:
        return str(frac.numerator // frac.denominator)
    else:
        whole = frac.numerator // frac.denominator
        remainder = frac.numerator % frac.denominator
        return f"{whole} {remainder}/{frac.denominator}"
