from flask import Flask, request, jsonify
import pandas as pd
import os
import sys
from flask_cors import CORS

# Add models folder to sys.path to import model modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models')))

from scaler import process_recipe_request

app = Flask(__name__)
CORS(app)  # Enable CORS to allow cross-origin requests from frontend

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TRANSLATION_FILE = os.path.join(DATA_DIR, "ingredients_translation.xlsx")

# Load translation DataFrame at startup
try:
    ingredient_translations = pd.read_excel(TRANSLATION_FILE, engine='openpyxl')
except Exception as e:
    print(f"❌ Failed to load ingredients translation file: {e}")
    ingredient_translations = None

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Smart Recipe API is running 🚀"})

@app.route("/scale_recipe", methods=["POST"])
def scale_recipe():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400

    recipe_name = data.get("recipe_name")
    new_servings = data.get("new_servings")

    if not recipe_name or not new_servings:
        return jsonify({"error": "Both 'recipe_name' and 'new_servings' are required."}), 400

    if ingredient_translations is None:
        return jsonify({"error": "Translation data not loaded on server."}), 500

    try:
        result = process_recipe_request(recipe_name, int(new_servings), ingredient_translations)
        return jsonify(result)
    except Exception as e:
        # Return error message to client for debugging
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Run app on all interfaces on specified port
    app.run(host="0.0.0.0", port=port)
