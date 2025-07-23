import os
import pandas as pd
from models.translator import detect_and_translate
from models.rewriter import rewrite_instruction
from models.parser import extract_amount_and_unit  # ✅ updated import

# Path to main recipe file
DATA_PATH = os.path.join(os.path.dirname(__file__), '../data/recipe_data.xlsx')

# Path to ingredient translation file (ensure this exists)
TRANSLATION_PATH = os.path.join(os.path.dirname(__file__), '../data/ingredients_translation.xlsx')



def process_recipe_request(recipe_name: str, new_servings: int):
    # Load Excel files
    xls = pd.ExcelFile(DATA_PATH)
    recipes_df = xls.parse("recipes")
    ingredients_df = xls.parse("ingredients")
    instructions_df = xls.parse("instructions")

    translation_df = pd.read_excel(TRANSLATION_PATH)

    # Filter recipe
    recipe_row = recipes_df[recipes_df['name'].str.lower() == recipe_name.lower()]
    if recipe_row.empty:
        raise ValueError("Recipe not found.")

    original_servings = int(recipe_row.iloc[0]['servings'])
    original_cook_time = int(recipe_row.iloc[0]['cook_time'])

    # Detect language based on the ingredients column
    language_column = [col for col in ingredients_df.columns if col.lower() not in ['recipe_name', 'amount', 'unit']][-1]
    lang = detect_and_translate(ingredients_df[language_column].iloc[0], detect_only=True).lower()

    # Filter ingredients and instructions for the specific recipe
    recipe_ingredients = ingredients_df[ingredients_df['recipe_name'].str.lower() == recipe_name.lower()]
    recipe_steps = instructions_df[instructions_df['recipe_name'].str.lower() == recipe_name.lower()]

    # Process ingredients with scaling and translation
    scaled_ingredients = []
    for _, row in recipe_ingredients.iterrows():
        ing_name_local = row[language_column]
        unit = row.get('unit', '')
        raw_amt = row.get('amount', '')

        parsed_amt, _ = extract_amount_and_unit(str(raw_amt))  # ✅ updated function
        scaled_amt = parsed_amt * new_servings / original_servings

        # Translate to English using translation DataFrame if language is not English
        translated_name = ing_name_local
        if lang != "en":
            match = translation_df[translation_df[lang].str.lower() == ing_name_local.lower()]
            if not match.empty:
                translated_name = match.iloc[0]['en']

        scaled_ingredients.append({
            'ingredient': translated_name,
            'amount': format_fraction(scaled_amt),
            'unit': unit
        })

    # Adjusted cook time (simple scaling logic)
    est_cook_time = int(original_cook_time + 0.1 * (new_servings - original_servings) * original_cook_time)

    # Rewrite instructions using translated and scaled ingredients
    updated_instructions = []
    for _, row in recipe_steps.iterrows():
        original_step = row[language_column]
        rewritten = rewrite_instruction(original_step, scaled_ingredients)
        updated_instructions.append(rewritten)

    return {
        'recipe_name': recipe_name,
        'original_servings': original_servings,
        'new_servings': new_servings,
        'estimated_cook_time': f"{est_cook_time} minutes",
        'ingredients': scaled_ingredients,
        'instructions': updated_instructions,
        'language_detected': lang
    }


def format_fraction(amount: float) -> str:
    """Format number into fractions like 1/2, 1 1/4, etc."""
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
