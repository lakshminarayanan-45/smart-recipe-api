# generate_scaler.py
import joblib
import numpy as np
from sklearn.linear_model import LinearRegression

# === Dummy data for ingredient scaling ===
# Format: [[ingredient_amount, servings], scaled_amount]
X = [
    [1, 2],
    [2, 2],
    [3, 2],
    [1, 4],
    [2, 4],
    [3, 4],
    [1, 6],
    [2, 6],
    [3, 6],
]

y = [
    1,
    2,
    3,
    2,
    4,
    6,
    3,
    6,
    9,
]

# === Train simple model ===
model = LinearRegression()
model.fit(X, y)

# === Save model as ingredient_scaler.pkl ===
joblib.dump(model, 'ingredient_scaler.pkl')

print("✅ ingredient_scaler.pkl file generated successfully!")
