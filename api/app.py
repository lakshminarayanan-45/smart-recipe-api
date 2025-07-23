from flask import Flask, request, jsonify
from models.scaler import process_recipe_request

app = Flask(__name__)

@app.route("/scale_recipe", methods=["POST"])
def scale_recipe():
    data = request.get_json()
    name = data.get("recipe_name")
    servings = data.get("new_servings")

    if not name or not servings:
        return jsonify({"error": "recipe_name and new_servings are required."}), 400

    try:
        result = process_recipe_request(name, int(servings))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
