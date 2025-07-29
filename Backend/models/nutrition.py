import os
import pandas as pd
import re
from thefuzz import process

# Adjust paths according to your backend structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

FOOD_CSV = os.path.join(DATA_DIR, 'food.csv')
NUTRIENT_CSV = os.path.join(DATA_DIR, 'nutrient.csv')
FOOD_NUTRIENT_CSV = os.path.join(DATA_DIR, 'food_nutrient.csv')

# Load USDA datasets once
food_df = pd.read_csv(FOOD_CSV)
nutrient_df = pd.read_csv(NUTRIENT_CSV)
food_nutrient_df = pd.read_csv(FOOD_NUTRIENT_CSV, low_memory=False)

food_df['desc_clean'] = food_df['description'].str.lower().str.strip()
nutrient_df = nutrient_df[nutrient_df['rank'] != 999999].copy()
nutrient_map = nutrient_df.set_index('id')[['name', 'unit_name']].to_dict('index')

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
    # Add other languages similarly if required
}

def parse_ingredient_line(line):
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
        return qty  # treat unknown as grams

def fuzzy_match(ingredient, choices, threshold=60):
    result = process.extractOne(ingredient, choices, score_cutoff=threshold)
    return result[0] if result else None

def get_nutrition(ingredient, quantity, unit):
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
    scale = grams / 100.0
    result = {}

    for _, row in f_nutr.iterrows():
        nid = row['nutrient_id']
        info = nutrient_map.get(nid)
        if info and info['name'] in focus_nutrients:
            value = row['amount'] * scale
            name = name_alias.get(info['name'], info['name'])
            result[name] = result.get(name, 0.0) + value
    return result

def get_nutrition_for_recipe(recipe_name, detect_language_func, lang_code_override=None):
    sheet_name, lang_col, lang_code, match_df = detect_language_func(recipe_name)
    if match_df is None or match_df.empty:
        raise ValueError(f"Recipe '{recipe_name}' not found.")
    row = match_df.iloc[0]

    if lang_code_override:
        lang_code = lang_code_override

    ingredient_col = None
    for col in row.index:
        if 'ingredient' in col.lower() and 'english' in col.lower():
            ingredient_col = col
            break
    if not ingredient_col:
        if 'ingredients_en' in row.index:
            ingredient_col = 'ingredients_en'
        else:
            return {}

    ingredient_text = str(row[ingredient_col])
    ingredient_lines = [x.strip() for x in re.split(r",|\n", ingredient_text) if x.strip()]

    total_nutrition = {}

    for line in ingredient_lines:
        parsed = parse_ingredient_line(line)
        if not parsed:
            continue
        p = parsed[0]
        nut = get_nutrition(p['name'], p['amount'], p['unit'])
        for k, v in nut.items():
            total_nutrition[k] = total_nutrition.get(k, 0.0) + v

    translated_nutrition = {
        translate_nutrient_name(k, lang_code): f"{round(v, 2)} {'kcal' if k == 'Calories' else 'g'}"
        for k, v in total_nutrition.items()
    }
    return translated_nutrition
