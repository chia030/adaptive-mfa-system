import torch
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from train_risk_model import RiskModel  # or wherever your class is defined
from preprocess import X_test, y_test   # your preprocessed test data
import matplotlib.pyplot as plt

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 1) Re‑instantiate and load the best model
model = RiskModel(input_dim=X_test.shape[1]).to(device)
model.load_state_dict(torch.load("./risk_model_best.pth", map_location=device))
model.eval()

# 2) Run predictions
with torch.no_grad():
    X_tensor = torch.from_numpy(X_test).float().to(device)
    preds    = model(X_tensor).cpu().numpy().flatten()

# 3) Compute regression metrics
mse = mean_squared_error(y_test, preds)
mae = mean_absolute_error(y_test, preds)
r2  = r2_score(y_test, preds)

print(f"Test MSE: {mse:.4f}") # MSE (Mean Squared Error): average squared difference. Lower is better.
print(f"Test MAE: {mae:.4f}") # MAE (Mean Absolute Error): average absolute difference. More interpretable.
print(f"Test R²:  {r2:.4f}") # R² (“explained variance”): fraction of variance explained (0→1). Closer to 1 is better.

plt.scatter(y_test, preds, alpha=0.3)
plt.plot([0,100],[0,100], 'k--')  # perfect prediction line
plt.xlabel("True Risk Score")
plt.ylabel("Predicted Risk Score")
plt.title("Predictions vs. True Values")
plt.show()
