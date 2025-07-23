import os
import pandas as pd
from models.translator import detect_and_translate
from models.rewriter import rewrite_instruction
from models.parser import parse_amount

DATA_PATH = os.path.join(os.path.dirname(__file__), '../data/recipes.xlsx')


def process_recipe_request(recipe_name: str, new_servings: int):
    # Load Excel file
    xls = pd.ExcelFile(DATA_PATH)
    recipes_df = xls.parse("recipes")
    ingredients_df = xls.parse("ingredients")
    instructions_df = xls.parse("instructions")

    # Filter recipe
    recipe_row = recipes_df[recipes_df['name'].str.lower() == recipe_name.lower()]
    if recipe_row.empty:
        raise ValueError("Recipe not found")

    original_servings = int(recipe_row.iloc[0]['servings'])
    original_cook_time = int(recipe_row.iloc[0]['cook_time'])

    # Detect language from ingredient or instructions column
    language_column = [col for col in ingredients_df.columns if col.lower() not in ['recipe_name', 'amount', 'unit']][-1]
    lang = detect_and_translate(ingredients_df[language_column].iloc[0], detect_only=True)

    # Filter ingredients and instructions
    recipe_ingredients = ingredients_df[ingredients_df['recipe_name'].str.lower() == recipe_name.lower()]
    recipe_steps = instructions_df[instructions_df['recipe_name'].str.lower() == recipe_name.lower()]

    # Scale ingredients
    scaled_ingredients = []
    for _, row in recipe_ingredients.iterrows():
        ing_name = row[language_column]
        unit = row.get('unit', '')
        raw_amt = row.get('amount', '')

        parsed_amt = parse_amount(str(raw_amt))
        scaled_amt = parsed_amt * new_servings / original_servings

        scaled_ingredients.append({
            'ingredient': ing_name,
            'amount': scaled_amt,
            'unit': unit
        })

    # Adjusted time
    est_cook_time = int(original_cook_time + 0.1 * (new_servings - original_servings) * original_cook_time)

    # Rewrite instructions
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
        'language': lang
    }

