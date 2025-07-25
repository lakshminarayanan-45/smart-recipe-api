import os
import pandas as pd
from models.translator import detect_and_translate
from models.rewriter import rewrite_instruction
from models.parser import extract_amount_and_unit

# Compute base directory - one level up from models/ is Backend/
BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))
DATA_PATH = os.path.join(BASE_DIR, "data", "recipe_data.xlsx")

def process_recipe_request(recipe_name: str, new_servings: int, translation_df: pd.DataFrame, cuisine_sheet: str = "North Indian"):
    """
    Process a recipe request using a specific cuisine sheet from the merged Excel file.

    :param recipe_name: Name of the recipe (case-insensitive)
    :param new_servings: Number of servings to scale to
    :param translation_df: DataFrame for ingredient translations
    :param cuisine_sheet: Sheet name to use in Excel file
    :return: dict with scaled recipe data
    """

    # Load sheet data explicitly
    xls = pd.ExcelFile(DATA_PATH, engine='openpyxl')

    # Validate sheet exists
    if cuisine_sheet not in xls.sheet_names:
        raise ValueError(f"Worksheet '{cuisine_sheet}' not found in Excel file. Available sheets: {xls.sheet_names}")

    df = xls.parse(cuisine_sheet)

    # Normalize column names to lower for ease
    df.columns = [col.lower() for col in df.columns]

    # Find the recipe row by name (case insensitive)
    recipe_row = df[df['name'].str.lower() == recipe_name.lower()]
    if recipe_row.empty:
        raise ValueError(f"Recipe '{recipe_name}' not found in sheet '{cuisine_sheet}'.")

    recipe_row = recipe_row.iloc[0]

    # Extract servings and cooking time (with fallback defaults)
    original_servings = int(recipe_row.get('servings', 1))
    original_cook_time = int(recipe_row.get('cooking', 0))  # Adjust column name if different

    # Extract ingredients and instructions text columns - expected format:
    ingredients_raw = recipe_row.get('ingredients_en', '')
    instructions_raw = recipe_row.get('instructions_en', '')

    # TODO: You need to parse `ingredients_raw` and `instructions_raw` strings into lists
    # For example, if ingredients are separated by newline or commas, split on that:
    # This part depends on your data format.

    # Simple parsing example (customize for your data!)
    ingredients_list = [line.strip() for line in str(ingredients_raw).split('\n') if line.strip()]
    instructions_list = [line.strip() for line in str(instructions_raw).split('\n') if line.strip()]

    # We now construct a DataFrame for ingredients similar to your old code structure to scale
    # But since we lack unit/amount columns, you might need to parse amounts and units from string
    # This example assumes each ingredient contains amount and unit somehow (you may improve parsing)

    scaled_ingredients = []
    for ing in ingredients_list:
        # Parse amount and unit from ingredient string using your parser function
        parsed_amt, unit = extract_amount_and_unit(ing)
        scaled_amt = parsed_amt * new_servings / original_servings
        # Extract just the ingredient name (you may want to improve this)
        # For this example, let's assume after amount and unit, the rest is name:
        # This depends on your string format, so you might need more NLP or rules.
        # As a fallback, use full string if extraction is complex:
        ing_name_local = ing

        # Translate ingredient name if needed
        translated_name = ing_name_local
        lang = "en"  # Since data is in English, set to 'en' or detect if you want

        if lang != "en":
            matches = translation_df[translation_df[lang].str.lower() == str(ing_name_local).lower()]
            if not matches.empty:
                translated_name = matches.iloc[0]['en']

        scaled_ingredients.append({
            "name": translated_name,
            "formattedAmount": format_fraction(scaled_amt),
            "unit": unit,
        })

    # Adjust cook time heuristically
    est_cook_time = int(original_cook_time + 0.1 * (new_servings - original_servings) * original_cook_time)

    # Rewrite instructions by injecting scaled ingredients (this depends on your rewriter code)
    updated_instructions = []
    for step in instructions_list:
        rewritten = rewrite_instruction(step, scaled_ingredients)
        updated_instructions.append(rewritten)

    return {
        "recipe": recipe_name,
        "original_servings": original_servings,
        "new_servings": new_servings,
        "original_time": f"{original_cook_time} minutes",
        "adjusted_time": f"{est_cook_time} minutes",
        "ingredients": scaled_ingredients,
        "steps": updated_instructions,
        "language_detected": lang,
    }

def format_fraction(amount: float) -> str:
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
