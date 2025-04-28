# print('Running Inference')

import torch
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
# from train_risk_model import RiskModel  # or wherever your class is defined
# from preprocess import X_test, y_test, X_train, y_train   # your preprocessed test data
import matplotlib.pyplot as plt
import joblib
from train_risk_model_rba import RiskModel  # import your MLP definition

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print('Running inference')

df = pd.read_csv("features.csv")
df.drop(columns=["label"], inplace=True)
input_dim = len(df.columns.tolist())
preproc = joblib.load("preprocessor.joblib")

# define arguments here (for now)
model_path = "risk_mlp.pt"
features = ["fail_60m", "succ_60m", "hour_dev", "device_unfamiliar", "country_change", "region_change", "impossible_travel", "ip_attack_rep"]
label = 'label'
hidden_dims = [128,64,32]
dropout = 0.3
lr = 1e-4
# epochs = 15
# model_out = "risk_mlp.pt"

# 1) Re‑instantiate and load the best model
def load_model(model_path: str):
    model = RiskModel(input_dim=input_dim,
                            hidden_dims=hidden_dims,
                            dropout=dropout)
    state = torch.load(model_path, map_location=device)
    model.load_state_dict(state)
    model.to(device).eval()
    return model

# model = RiskModel(input_dim=X_test.shape[1]).to(device)
# model.load_state_dict(torch.load("./risk_model_best.pth", map_location=device))
# model.eval()

# 2) Run inference
def run_inference(
    df: pd.DataFrame,
    feature_cols: list[str],
    model: torch.nn.Module,
    preprocessor,
    device: torch.device = None
) -> pd.Series:
    device = device

    # extract feature matrix
    X = df[feature_cols]

    # apply same preprocesing pipeline as in training
    X_proc = preprocessor.transform(X)

    # convert to torch.Tensor
    X_tensor = torch.from_numpy(X_proc).float().to(device)

    # forward pass & sigmoid to get probabilities
    with torch.no_grad():
        logits = model(X_tensor)
        probs = torch.sigmoid(logits)
    
    # return as flat pandas series aligned with df
    return pd.Series(probs.cpu().numpy().ravel(), index=df.index, name='risk_prob')

if __name__ == '__main__':
    # load data
    df_new = pd.read_csv("inference-data.csv")

    # load preprocessor and model
    # preproc = joblib.load('preprocessor.joblib')
    model = load_model('risk_mlp.pt')

    df_new['risk_prob'] = run_inference(df_new, feature_cols=features, model=model, preprocessor=preproc)

    # should be 
    # df_new['mfa_required'] = df_new['risk_prob'] >= chosen_thresh

    df_new.to_csv("inference_output.csv", index=False)
    print("Saved risk scores to inference_output.csv")

# with torch.no_grad():
#     X_tensor = torch.from_numpy(X_train).float().to(device)
#     preds    = model(X_tensor).cpu().numpy().flatten()

# 3) Compute regression metrics
#mse = mean_squared_error(y_test, preds)
#mae = mean_absolute_error(y_test, preds)
#r2  = r2_score(y_test, preds)

#print(f"Test MSE: {mse:.4f}") # MSE (Mean Squared Error): average squared difference. Lower is better.
#print(f"Test MAE: {mae:.4f}") # MAE (Mean Absolute Error): average absolute difference. More interpretable.
#print(f"Test R²:  {r2:.4f}") # R² (“explained variance”): fraction of variance explained (0→1). Closer to 1 is better.



# plt.scatter(y_train, preds, alpha=0.3)
# plt.plot([0,1],[0,1], 'k--')  # perfect prediction line
# plt.xlabel("True Risk Score")
# plt.ylabel("Predicted Risk Score")
# plt.title("Predictions vs. True Values")
# plt.show()
