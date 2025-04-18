import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from preprocess import load_and_preprocess, FEATURE_NAMES
from sklearn.model_selection import GridSearchCV
import matplotlib.pyplot as plt

# Load the same train/test data you use for the NN:
X_train, X_test, y_train, y_test = load_and_preprocess()

y_train = y_train * 100
y_test  = y_test  * 100

param_grid = {
  "max_depth": [3,5,7],
  "learning_rate": [0.01, 0.1, 0.2],
  "n_estimators": [50, 100, 200]
}

model = xgb.XGBRegressor(
    n_estimators=200, # number of trees
    max_depths=3, # maximum tree depth
    learning_rate=0.1, # shrinking factor
    objective="reg:squarederror",
    random_state=42
)

model.fit(X_train, y_train)
preds = model.predict(X_test)

importances = model.feature_importances_
feature_names = FEATURE_NAMES

mse = mean_squared_error(y_test, preds)
mae = mean_absolute_error(y_test, preds)
r2  = r2_score(y_test, preds)

print(f"XGBoost Test MSE:  {mse:.2f}")
print(f"XGBoost Test MAE:  {mae:.2f}")
print(f"XGBoost Test R²:   {r2:.3f}")

grid = GridSearchCV(
    xgb.XGBRegressor(objective="reg:squarederror", random_state=42),
    param_grid,
    cv=3,
    scoring="neg_mean_absolute_error",
    verbose=1
)
grid.fit(X_train, y_train)

print("Best params:", grid.best_params_)
best_model = grid.best_estimator_

plt.figure(figsize=(6,10))
plt.barh(feature_names, importances)
plt.xlabel("Importance")
plt.title("XGBoost Feature Importances")
plt.tight_layout()
plt.show()
