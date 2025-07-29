from flask import Flask, request, jsonify
import pandas as pd
import os
import sys
from flask_cors import CORS

# Append models path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models')))
from scaler import process_recipe_request, detect_language  # import detect_language function
from nutrition import get_nutrition_for_recipe  # import nutrition function

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TRANSLATION_FILE = os.path.join(DATA_DIR, "ingredients_translation.xlsx")

try:
    ingredient_translations = pd.read_excel(TRANSLATION_FILE, engine='openpyxl')
except Exception as e:
    print(f"❌ Failed to load ingredients translation file: {e}")
    ingredient_translations = None

API_KEY = os.environ.get("RECIPE_API_KEY")
if not API_KEY:
    raise RuntimeError("RECIPE_API_KEY environment variable not set! Please configure it in your deployment.")

def check_api_key():
    key = request.headers.get("X-API-KEY") or request.headers.get("Authorization")
    if key and key.lower().startswith("bearer "):
        key = key[7:]
    return key == API_KEY

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Smart Recipe API is running 🚀"})

@app.route("/scale_recipe", methods=["POST"])
def scale_recipe():
    if not check_api_key():
        return jsonify({"error": "Unauthorized: Invalid or missing API key"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    recipe_name = data.get("recipe_name")
    new_servings = data.get("new_servings")
    if not recipe_name or not new_servings:
        return jsonify({"error": "Both 'recipe_name' and 'new_servings' are required."}), 400
    if ingredient_translations is None:
        return jsonify({"error": "Translation file not loaded on server."}), 500

    try:
        result = process_recipe_request(recipe_name, int(new_servings), ingredient_translations)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/nutrition_info", methods=["POST"])
def nutrition_info():
    if not check_api_key():
        return jsonify({"error": "Unauthorized: Invalid or missing API key"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    recipe_name = data.get("recipe_name")
    lang_code = data.get("lang_code")  # optional

    if not recipe_name:
        return jsonify({"error": "'recipe_name' is required."}), 400

    try:
        nutrition_data = get_nutrition_for_recipe(recipe_name, detect_language, lang_code_override=lang_code)
        return jsonify({
            "recipe": recipe_name,
            "nutrition": nutrition_data,
            "language_detected": lang_code or "en"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
