from flask import Flask, request, jsonify
import pandas as pd
import os
from models.scaler import process_recipe_request

app = Flask(__name__)

# Load translation dataset once at startup
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "ingredient_translations.xlsx")
try:
    ingredient_translations = pd.read_excel(DATA_PATH)
except Exception as e:
    print(f"❌ Failed to load translation file: {e}")
    ingredient_translations = None  # Fail-safe in case file is missing

@app.route("/scale_recipe", methods=["POST"])
def scale_recipe():
    data = request.get_json()
    name = data.get("recipe_name")
    servings = data.get("new_servings")

    if not name or not servings:
        return jsonify({"error": "recipe_name and new_servings are required."}), 400

    if ingredient_translations is None:
        return jsonify({"error": "Translation file not loaded."}), 500

    try:
        result = process_recipe_request(name, int(servings), ingredient_translations)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render assigns dynamic port
    app.run(host="0.0.0.0", port=port)
