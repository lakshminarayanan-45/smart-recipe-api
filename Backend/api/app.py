from flask import Flask, request, jsonify
import pandas as pd
import os
import sys
from flask_cors import CORS  # Enable CORS

# Add the models folder (which is sibling to api/) to Python path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models')))
from scaler import process_recipe_request

app = Flask(__name__)
CORS(app)  # Allow cross-origin frontend calls

# Compute absolute path to Backend/data/ directory, one level up from api/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Backend/
DATA_DIR = os.path.join(BASE_DIR, "data")
TRANSLATION_FILE = os.path.join(DATA_DIR, "ingredients_translation.xlsx")

try:
    print(f"Loading translation file from: {TRANSLATION_FILE}")
    # Explicitly specify engine='openpyxl' to avoid Excel format errors
    ingredient_translations = pd.read_excel(TRANSLATION_FILE, engine='openpyxl')
except Exception as e:
    print(f"❌ Failed to load translation file: {e}")
    ingredient_translations = None  # Fail-safe if missing

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Smart Recipe API is running 🚀"})

@app.route("/scale_recipe", methods=["POST"])
def scale_recipe():
    data = request.get_json()
    name = data.get("recipe_name")
    new_servings = data.get("new_servings")

    if not name or not new_servings:
        return jsonify({"error": "recipe_name and new_servings are required."}), 400

    if ingredient_translations is None:
        return jsonify({"error": "Translation file not loaded."}), 500

    try:
        result = process_recipe_request(name, int(new_servings), ingredient_translations)
        return jsonify(result)
    except Exception as e:
        # Log error to console for debugging
        print(f"Error in processing request: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
