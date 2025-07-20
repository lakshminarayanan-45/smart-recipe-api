import joblib
import numpy as np
from sklearn.linear_model import LinearRegression

# === Training Data ===
# Assume simple linear data: original qty = 1 at 2 servings ➡ scale linearly
X = []
y = []

# Generate dummy data (e.g., 1–5 units at servings from 1 to 10)
for qty in range(1, 6):  # original quantity
    for servings in range(1, 11):  # servings from 1 to 10
        X.append([qty, servings])
        # Assuming linear scale based on servings
        y.append(qty * servings / 2)

X = np.array(X)
y = np.array(y)

# === Train Model ===
model = LinearRegression()
model.fit(X, y)

# === Export Model ===
joblib.dump(model, "ingredient_scaler.pkl")
print("✅ Model trained and saved as ingredient_scaler.pkl")
