import pandas as pd
from utils import format_quantity

EXCEL_FILE = "data/recipes.xlsx"


def process_recipe_request(recipe_name, new_servings):
    df = pd.read_excel(EXCEL_FILE)
    df_recipe = df[df['recipe_name'].str.lower() == recipe_name.lower()]
    if df_recipe.empty:
        raise ValueError(f"Recipe '{recipe_name}' not found")

    old_servings = df_recipe['servings'].iloc[0]
    time = df_recipe['cooking_time'].iloc[0]

    scaled_ingredients = []
    for _, row in df_recipe.iterrows():
        orig_amt = row['amount']
        unit = row['unit']
        ing = row['ingredient_name']
        scale_amt = (orig_amt / old_servings) * new_servings
        formatted = format_quantity(scale_amt)
        scaled_ingredients.append({"ingredient": ing, "amount": formatted, "unit": unit})

    estimated_time = int((new_servings / old_servings) * time)
    return {
        "recipe_name": recipe_name,
        "new_servings": new_servings,
        "estimated_time": f"{estimated_time} minutes",
        "ingredients": scaled_ingredients
    }
