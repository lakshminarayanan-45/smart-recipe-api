import os
import pandas as pd
import re
from thefuzz import process

# You may need to adjust import path depending on your module structure
# from models.scaler import detect_language  # or wherever detect_language lives in your repo
# For now, consider detect_language imported from scaler or nutrition.py caller providing it

# ==================== Data Paths ====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Adjust as per your folder structure
DATA_DIR = os.path.join(BASE_DIR, "data")

FOOD_CSV = os.path.join(DATA_DIR, 'food.csv')
NUTRIENT_CSV = os.path.join(DATA_DIR, 'nutrient.csv')
FOOD_NUTRIENT_CSV = os.path.join(DATA_DIR, 'food_nutrient.csv')

# ==================== Load Datasets ====================
food_df = pd.read_csv(FOOD_CSV)
nutrient_df = pd.read_csv(NUTRIENT_CSV)
food_nutrient_df = pd.read_csv(FOOD_NUTRIENT_CSV, low_memory=False)

# Clean USDA data
food_df['desc_clean'] = food_df['description'].str.lower().str.strip()
nutrient_df = nutrient_df[nutrient_df['rank'] != 999999].copy()
nutrient_map = nutrient_df.set_index('id')[['name', 'unit_name']].to_dict('index')

# Focus nutrients and their aliases (to show friendly names)
focus_nutrients = [
    "Energy", "Energy (Atwater General Factors)", "Energy (Atwater Specific Factors)",
    "Protein", "Total lipid (fat)", "Carbohydrate, by difference", "Fiber, total dietary",
    "Sugars, total including NLEA", "Cholesterol", "Sodium, Na",
    "Calcium, Ca", "Iron, Fe", "Potassium, K"
]

name_alias = {
    "Energy": "Calories", "Energy (Atwater General Factors)": "Calories",
    "Energy (Atwater Specific Factors)": "Calories", "Protein": "Protein",
    "Total lipid (fat)": "Fat", "Carbohydrate, by difference": "Carbohydrates",
    "Fiber, total dietary": "Fiber", "Sugars, total including NLEA": "Sugar",
    "Cholesterol": "Cholesterol", "Sodium, Na": "Sodium",
    "Calcium, Ca": "Calcium", "Iron, Fe": "Iron", "Potassium, K": "Potassium"
}

# Nutrient translation dictionary for supported languages (extend if needed)
nutrient_name_translations = {
    'en': {k: k for k in name_alias.values()},
    'ta': {
        'Calories': 'கேலரிகள்', 'Protein': 'புரதம்', 'Fat': 'கொழுப்பு',
        'Carbohydrates': 'கார்போஹைட்ரேட்டுகள்', 'Fiber': 'நார்', 'Sugar': 'சர்க்கரை',
        'Cholesterol': 'கொலஸ்ட்ரால்', 'Sodium': 'சோடியம்',
        'Calcium': 'கால்சியம்', 'Iron': 'இரும்பு', 'Potassium': 'பொட்டாசியம்'
    },
    'hn': {
        'Calories': 'कैलोरी', 'Protein': 'प्रोटीन', 'Fat': 'वसा',
        'Carbohydrates': 'कार्बोहाइड्रेट', 'Fiber': 'रेशा', 'Sugar': 'शुगर',
        'Cholesterol': 'कोलेस्ट्रॉल', 'Sodium': 'सोडियम',
        'Calcium': 'कैल्शियम', 'Iron': 'लोहा', 'Potassium': 'पोटैशियम'
    },
    # Add other languages as needed following the same pattern
}

# ==================== Utility Functions ====================

def parse_ingredient_line(line):
    """ Parse string of ingredients into structured dict list with amount, unit, name """
    items = [i.strip() for i in re.split(r",|\n", str(line)) if i.strip()]
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
            result.append({
                "amount": amount,
                "unit": unit.strip(),
                "name": match.group(3).strip(),
                "formattedAmount": f"{round(amount, 2)}"
            })
    return result

def translate_nutrient_name(nutrient, lang_code):
    """ Translate nutrient name based on language code """
    return nutrient_name_translations.get(lang_code, {}).get(nutrient, nutrient)

def convert_to_grams(qty, unit):
    u = unit.lower()
    if u in ['g', 'gram', 'grams']:
        return qty
    elif u in ['kg', 'kilogram', 'kilograms']:
        return qty * 1000
    elif u in ['mg', 'milligram', 'milligrams']:
        return qty / 1000
    elif u in ['lb', 'pound', 'pounds']:
        return qty * 453.592
    elif u in ['oz', 'ounce', 'ounces']:
        return qty * 28.3495
    else:
        return qty  # Unknown units treated as grams for simplicity

def fuzzy_match(ingredient, choices, threshold=60):
    result = process.extractOne(ingredient, choices, score_cutoff=threshold)
    return result[0] if result else None

def get_nutrition(ingredient, quantity, unit):
    """
    Lookup nutrition info for a single ingredient quantity in USDA data.
    Returns dict with nutrient names and values scaled to quantity.
    """
    cleaned_name = ingredient.lower().strip()
    best_match = fuzzy_match(cleaned_name, food_df['desc_clean'])
    if not best_match:
        return {}
    matched_rows = food_df[food_df['desc_clean'] == best_match]
    best_fdc_id = None
    best_score = 0
    for fid in matched_rows['fdc_id'].values:
        f_nutr = food_nutrient_df[food_nutrient_df['fdc_id'] == fid]
        count = sum(1 for _, r in f_nutr.iterrows() if nutrient_map.get(r['nutrient_id'], {}).get('name') in focus_nutrients)
        if count > best_score:
            best_score = count
            best_fdc_id = fid
    if not best_fdc_id:
        return {}

    f_nutr = food_nutrient_df[food_nutrient_df['fdc_id'] == best_fdc_id]
    grams = convert_to_grams(quantity, unit)
    scale = grams / 100.0  # USDA nutrient values are per 100 grams
    result = {}

    for _, row in f_nutr.iterrows():
        nid = row['nutrient_id']
        info = nutrient_map.get(nid)
        if info and info['name'] in focus_nutrients:
            value = row['amount'] * scale
            name = name_alias.get(info['name'], info['name'])
            result[name] = result.get(name, 0.0) + value
    return result

# ==================== Main Function to Call from Backend ====================

def get_nutrition_for_recipe(recipe_name, detect_language_func, lang_code_override=None):
    """
    Given a recipe_name and a detect_language function (from scaler or elsewhere),
    returns total nutrition dict for the recipe ingredients.
    
    :param recipe_name: str, recipe name to search in recipe sheet
    :param detect_language_func: function, must have signature like your existing detect_language
    :param lang_code_override: optional, force language code for nutrient translations

    :return: dict with nutrients summed up and translated keys if lang_code_override provided
    """
    # 1. Detect which sheet, language column, language code, and matched row
    sheet_name, lang_col, lang_code, match_df = detect_language_func(recipe_name)
    if match_df is None or match_df.empty:
        raise ValueError(f"Recipe '{recipe_name}' not found.")
    row = match_df.iloc[0]

    # Override if lang_code_override provided (e.g., frontend request language)
    if lang_code_override:
        lang_code = lang_code_override

    # 2. Find English ingredient column (similar logic as before)
    ingredient_col = None
    for col in row.index:
        if 'ingredient' in col.lower() and 'english' in col.lower():
            ingredient_col = col
            break
    if not ingredient_col:
        if 'ingredients_en' in row.index:
            ingredient_col = 'ingredients_en'
        else:
            # Could not find column - return empty
            return {}

    # 3. Parse ingredient lines
    ingredient_text = str(row[ingredient_col])
    ingredient_lines = [x.strip() for x in re.split(r",|\n", ingredient_text) if x.strip()]
    
    total_nutrition = {}

    # 4. For each ingredient line, parse and sum nutrient values
    for line in ingredient_lines:
        parsed = parse_ingredient_line(line)
        if not parsed:
            continue
        # Take first parsed item (usually only one)
        p = parsed[0]
        nut = get_nutrition(p['name'], p['amount'], p['unit'])
        for k, v in nut.items():
            total_nutrition[k] = total_nutrition.get(k, 0.0) + v

    # 5. Translate nutrient names if needed
    translated_nutrition = {
        translate_nutrient_name(k, lang_code): f"{round(v, 2)} {'kcal' if k == 'Calories' else 'g'}"
        for k, v in total_nutrition.items()
    }
    return translated_nutrition
