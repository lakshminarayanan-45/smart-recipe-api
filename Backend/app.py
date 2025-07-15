import os
import re
from fractions import Fraction
from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
import pandas as pd
import joblib  # ✅ Using joblib consistently

# === Configuration ===
API_KEY = os.getenv("API_KEY", "abc123securetoken")
EXCEL_PATH = os.getenv("RECIPE_XLSX", os.path.join(os.path.dirname(__file__), "recipe_data.xlsx"))
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(__file__), "ingredient_scaler.pkl"))
BASE_SERVINGS = 2

# === Load Excel ===
try:
    xls = pd.read_excel(EXCEL_PATH, sheet_name=None, engine="openpyxl")
except FileNotFoundError:
    raise RuntimeError(f"❌ Excel file not found: {EXCEL_PATH}")

# === Load ML Model using joblib ===
try:
    scaler_model = joblib.load(MODEL_PATH)
except FileNotFoundError:
    raise RuntimeError(f"❌ ML model file not found: {MODEL_PATH}")
except Exception as e:
    raise RuntimeError(f"❌ Error loading ML model: {str(e)}")

LANGUAGE_SUFFIX = {
    "TamilName": "ta", "tamilname": "ta", "hindiName": "hn", "malayalamName": "kl",
    "kannadaName": "kn", "teluguName": "te", "frenchName": "french",
    "spanishName": "spanish", "germanName": "german"
}

# === Flask App Setup ===
app = Flask(__name__, static_folder="static")
CORS(app)

# === Helpers ===
def to_mixed_fraction(val: float, precision=1/8) -> str:
    frac = Fraction(val).limit_denominator(int(1 / precision))
    whole, remainder = divmod(frac.numerator, frac.denominator)
    return f"{whole} and {Fraction(remainder, frac.denominator)}" if remainder else str(whole)

def format_time(minutes):
    try:
        m = int(round(float(minutes)))
        hrs, mins = divmod(m, 60)
        return (f"{hrs} hr{'s' if hrs > 1 else ''} " if hrs else "") + (f"{mins} min{'s' if mins > 1 else ''}" if mins else "")
    except Exception:
        return str(minutes)

def detect_row(recipe_name):
    lower = recipe_name.lower()
    for sheet, df in xls.items():
        for lang_col in LANGUAGE_SUFFIX:
            if lang_col in df.columns:
                match = df[df[lang_col].astype(str).str.lower().str.strip() == lower]
                if not match.empty:
                    return sheet, lang_col, LANGUAGE_SUFFIX[lang_col], match
        for col in ("name", "Name"):
            if col in df.columns:
                match = df[df[col].astype(str).str.lower().str.strip() == lower]
                if not match.empty:
                    return sheet, col, "en", match
    return None, None, None, None

def parse_ingredients(raw):
    lines = re.split(r",|\n", str(raw))
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m1 = re.match(r"(?P<qty>[\d\./]+)?\s*(?P<unit>\w+)?\s+(?P<name>[a-zA-Z].+)", line)
        m2 = re.match(r"(?P<name>.+?)\s*[-:]\s*(?P<qty>[\d\./]+)?\s*(?P<unit>\w+)?", line)

        match = m1 or m2
        if match:
            try:
                qty = eval(match.group("qty")) if match.group("qty") else 1
            except Exception:
                qty = 1
            result.append({
                "amount": qty,
                "unit": match.group("unit") or "",
                "name": match.group("name").strip(),
                "formattedAmount": f"{round(qty, 2)}"
            })
    return result

def scale_ingredient_ml(item, servings):
    qty = item["amount"]
    features = [[qty, servings]]
    scaled = scaler_model.predict(features)[0]
    return {
        **item,
        "amount": round(scaled, 2),
        "formattedAmount": to_mixed_fraction(scaled)
    }

# === Auth Decorator ===
def require_key(fn):
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != API_KEY:
            abort(401, description="Unauthorized")
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

# === Routes ===
@app.route("/adjust_ingredients", methods=["POST"])
@require_key
def adjust_ingredients():
    payload = request.get_json(force=True)
    recipe = payload.get("recipe_name", "").strip()
    servings = int(payload.get("servings", BASE_SERVINGS))

    sheet, lang_col, lang_code, df_row = detect_row(recipe)
    if df_row is None:
        return jsonify({"error": "Recipe not found"}), 404

    row = df_row.iloc[0]
    ing_col = next((c for c in row.index if f"ingredients_{lang_code}" in c.lower()), None) \
              or next((c for c in row.index if "ingredients_en" in c.lower()), None)

    if not ing_col:
        return jsonify({"error": "Ingredient column not found"}), 500

    cook_col = next((c for c in row.index if c.lower() in ("cooking", "cookingtime")), None)
    original_time = row[cook_col] if cook_col else "N/A"

    base_ingredients = parse_ingredients(row[ing_col])
    adjusted_ingredients = [scale_ingredient_ml(i, servings) for i in base_ingredients]

    return jsonify({
        "recipe": recipe,
        "base_servings": BASE_SERVINGS,
        "new_servings": servings,
        "original_time": format_time(original_time),
        "adjusted_time": format_time(original_time),
        "ingredients": adjusted_ingredients
    })

@app.route("/")
def root():
    return send_from_directory("static", "index.html")

# === Entry Point ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
