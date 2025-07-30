import os
import pandas as pd
import re
from thefuzz import process

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FOOD_CSV = os.path.join(DATA_DIR, 'food.csv')
NUTRIENT_CSV = os.path.join(DATA_DIR, 'nutrient.csv')
FOOD_NUTRIENT_CSV = os.path.join(DATA_DIR, 'food_nutrient.csv')

# Load USDA datasets once at module load
food_df = pd.read_csv(FOOD_CSV)
nutrient_df = pd.read_csv(NUTRIENT_CSV)
food_nutrient_df = pd.read_csv(FOOD_NUTRIENT_CSV, low_memory=False)

print(f"[Nutrition] FDA datasets: food: {len(food_df)}, nutrient: {len(nutrient_df)}, food_nutrient: {len(food_nutrient_df)}")

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
    # Add more if needed
}

# Manual mappings for common unmatched or regional ingredients
manual_ingredient_mapping = {
    "jaggery": "brown sugar",
    "ghee": "butter oil",
    "red chilli powder": "spices, chili powder",
    "cinnamon stick": "spices, cinnamon",
    "cardamom pods": "spices, cardamom",
    "cumin powder": "spices, cumin seed",
    "garam masala powder": "spices, curry powder",
    "chicken": "chicken, broilers or fryers, meat only, raw",
    "oil": "oil, vegetable",
    "onions": "onions, raw",
    "ginger garlic paste": "garlic",
    "turmeric powder": "spices, turmeric, ground",
    "tomatoes": "tomatoes, red, ripe, raw, year round average",
    "cloves": "spices, cloves",
    "salt": "salt, table",
    "water": None,  # Skip, water has negligible nutrients
    "coriander leaves": "cilantro",
    "cardamom": "spices, cardamom",
    "cinnamon": "spices, cinnamon",
    "chilli": "spices, chili powder",
    "chili": "spices, chili powder",
    "red chillie powder": "spices, chili powder",
    # Add more as you see unmatched ingredients
}

def clean_ingredient_name(name):
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)  # remove punctuation
    stop_words = [
        'powder', 'fresh', 'pinch', 'to taste', 'optional', 'chopped',
        'sliced', 'diced', 'stick', 'pods', 'large', 'for garnishing', 'paste'
    ]
    for sw in stop_words:
        name = name.replace(sw, '')
    name = re.sub(r'\s+', ' ', name).strip()
    # Apply manual mapping if available
    if name in manual_ingredient_mapping:
        mapped = manual_ingredient_mapping[name]
        print(f"[Nutrition] Manual map: '{name}' -> '{mapped}'")
        return mapped
    return name

def parse_ingredient_line(line):
    items = [i.strip() for i in re.split(r",|\n", str(line)) if i.strip()]
    parsed_items = []
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
            parsed_items.append({
                "amount": amount,
                "unit": unit.strip(),
                "name": name,
                "formattedAmount": f"{round(amount, 2)}"
            })
    return parsed_items

def translate_nutrient_name(nutrient, lang_code):
    return nutrient_name_translations.get(lang_code, {}).get(nutrient, nutrient)

def convert_to_grams(qty, unit):
    u = unit.lower()
    # Add common cooking units
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
    elif u in ['tbsp', 'tablespoon', 'tablespoons']:
        return qty * 14.2
    elif u in ['tsp', 'teaspoon', 'teaspoons']:
        return qty * 4.7
    elif u in ['cup', 'cups']:
        return qty * 240
    elif u in ['pcs', 'piece', 'pieces', 'unit', 'units']:
        return qty * 50
    else:
        print(f"[Nutrition] Unknown unit '{unit}', treating {qty} as grams.")
        return qty

def fuzzy_match(ingredient, choices, threshold=50):
    # Return best matched candidate
    results = process.extract(ingredient, choices, limit=3)
    if results:
        print(f"[Nutrition] Top USDA matches for '{ingredient}': {results}")
    result = [r for r in results if r[1] >= threshold]
    return result[0][0] if result else None

def get_nutrition(ingredient, quantity, unit):
    cleaned_name = clean_ingredient_name(ingredient)
    if cleaned_name is None:
        print(f"[Nutrition] Ingredient '{ingredient}' intentionally skipped.")
        return {}
    best_match = fuzzy_match(cleaned_name, food_df['desc_clean'])
    print(f"[Nutrition] Ingredient '{ingredient}' cleaned as '{cleaned_name}'; matched with '{best_match}'")
    if not best_match:
        print(f"[Nutrition] No USDA match found for '{cleaned_name}'")
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
        print(f"[Nutrition] No nutrient data for '{best_match}'")
        return {}

    f_nutr = food_nutrient_df[food_nutrient_df['fdc_id'] == best_fdc_id]
    grams = convert_to_grams(quantity, unit)
    scale = grams / 100.0  # All nutrients per 100g
    result = {}
    for _, row in f_nutr.iterrows():
        nid = row['nutrient_id']
        info = nutrient_map.get(nid)
        if info and info['name'] in focus_nutrients:
            value = row['amount'] * scale
            name = name_alias.get(info['name'], info['name'])
            result[name] = result.get(name, 0.0) + value
    print(f"[Nutrition] Nutrition for '{ingredient}': {result}")
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
    print(f"[Nutrition] Total nutrition for '{recipe_name}': {translated_nutrition}")
    return translated_nutrition
