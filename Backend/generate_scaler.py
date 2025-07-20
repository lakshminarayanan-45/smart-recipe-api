import joblib
import numpy as np
from sklearn.linear_model import LinearRegression

# === Dummy Training Data ===
X = []
y = []

# Generate synthetic data: quantities 1–5, servings 1–10
for qty in range(1, 6):
    for servings in range(1, 11):
        X.append([qty, servings])
        # Rule: scaled_qty = (original_qty * new_servings / base_servings)
        y.append(qty * servings / 2)  # since base_servings = 2

X = np.array(X)
y = np.array(y)

# === Train Simple Linear Regression Model ===
model = LinearRegression()
model.fit(X, y)

# === Save Model ===
joblib.dump(model, "ingredient_scaler.pkl")
print("✅ Model trained and saved as ingredient_scaler.pkl")
