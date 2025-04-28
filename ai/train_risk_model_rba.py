import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.metrics import auc as a
from scipy.special import expit  # sigmoid

# y_true, y_score = 0

# dataset
class LoginDataset(Dataset):
    def __init__(self, csv_path, features, label, device):
        # X and y are numpy arrays after preprocessing
        df = pd.read_csv(csv_path)

        

        if label not in df.columns:
            raise ValueError(f"Label column '{label}' not found in {csv_path}")
        
        df = df.dropna(subset=[label])
        # print(df[label].dtype, df[label].unique())

        y_np = df[label].values.astype(np.float32)
        X_np = df[features].values.astype(np.float32)
        
        self.X = torch.from_numpy(X_np).to(device)
        self.y = torch.from_numpy(y_np).unsqueeze(1).to(device)  
        self.n = len(df)

        # print("CSV columns:", df.columns.tolist())
        # print("First few rows:\n", df.head(3))

        # print("Inside Dataset, y shape:", self.y.shape)
        # print("Inside Dataset, y unique:", torch.unique(self.y))
        
    def __len__(self):
        return  self.n

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# MLP
class RiskModel(nn.Module):
    def __init__(self, input_dim, hidden_dims=(64,32), dropout=0.2):
        super().__init__()
        layers = []
        prev = input_dim
        for h in hidden_dims:
            layers += [ nn.Linear(prev, h),
                        nn.ReLU(),
                        nn.Dropout(dropout) ]
            prev = h
        layers.append(nn.Linear(prev, 1)) # single logit
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

# training function
def train_epoch(model, loader, loss_fn, optimizer):
    model.train()
    total_loss = 0.0
    for Xb, yb in loader:
        optimizer.zero_grad()
        logits = model(Xb)
        loss = loss_fn(logits, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * Xb.size(0)
    return total_loss / len(loader.dataset)

# evaluation function
@torch.no_grad()
def eval_epoch(model, loader, loss_fn):
    model.eval()
    total_loss = 0.0
    all_logits = []
    all_labels = []
    for Xb, yb in loader:
        logits = model(Xb)
        total_loss += loss_fn(logits, yb).item() * Xb.size(0)
        all_logits.append(logits.cpu().numpy())
        all_labels.append(yb.cpu().numpy())
    avg_loss = total_loss / len(loader.dataset)
    logits = np.vstack(all_logits) # shape (N,1), continuous floats
    labels = np.vstack(all_labels) # shape (N,1), 0/1 ints

    # print("y_true shape:", labels.shape)
    # print("y_true dtype:", labels.dtype)
    # print("y_true unique values:", np.unique(labels))
    


    auc = roc_auc_score(labels, logits) # logits ok for AUC
    return avg_loss, auc

def main():
    # device setup
    global device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # define arguments here (for now)
    train_csv = "train_output.csv"
    test_csv = "test_output.csv"
    features = ["fail_60m", "succ_60m", "hour_dev", "device_unfamiliar", "country_change", "region_change", "impossible_travel", "ip_attack_rep"]
    label = 'label'
    batch_size = 128
    hidden_dims = [128,64,32]
    dropout = 0.3
    lr = 1e-5
    epochs = 15
    model_out = "risk_mlp.pt"

    # load datasets
    train_ds = LoginDataset(train_csv, features, label, device)
    test_ds = LoginDataset(test_csv, features, label, device)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    # model, loss, optimizer
    model = RiskModel(input_dim=len(features),
                      hidden_dims=hidden_dims,
                      dropout=dropout).to(device)
    loss_fn = nn.BCEWithLogitsLoss()
    # loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([reweight_factor]))
    optimizer = optim.Adam(model.parameters(), lr=lr)

    best_auc = 0.0
    for epoch in range(1, epochs+1):
        train_loss = train_epoch(model, train_loader, loss_fn, optimizer)
        val_loss, val_auc = eval_epoch(model, test_loader, loss_fn)

        print(f"Epoch {epoch:02d} | "
              f"Train Loss: {train_loss:.4f} | "
              f"Val Loss: {val_loss:.4f} | "
              f"Val AUC: {val_auc:.4f}")
        
        # checkpoint best model
        if val_auc > best_auc:
            best_auc = val_auc
            torch.save(model.state_dict(), model_out)

    all_logits = []
    all_labels = []
    for Xb, yb in test_loader:
        logits = model(Xb).detach().cpu().numpy().ravel()
        labels = yb.cpu().numpy().ravel()
        all_logits.append(logits)
        all_labels.append(labels)

    y_score = np.concatenate(all_logits)   # continuous scores
    y_true  = np.concatenate(all_labels)   # binary 0/1

    # Compute ROC curve
    probs = expit(y_score)   # now in [0,1]
    fpr, tpr, thresholds = roc_curve(y_true, probs)
    roc_auc = a(fpr, tpr)
    print(f"Final test-set AUC: {roc_auc:.4f}")

    opt_ix = np.argmax(tpr - fpr)
    opt_thresh = thresholds[opt_ix]

    print("Top 5 unique probs:", np.unique(probs)[-5:])
    print("Youden J index at index:", opt_ix)
    print("Raw optimal threshold =", repr(opt_thresh))
    print("TPR, FPR at that threshold:", tpr[opt_ix], fpr[opt_ix])

    # already have fpr, tpr, thresholds from roc_curve on probs
    max_fpr = 0.05                   # 5% max false positives
    valid_idxs = np.where(fpr <= max_fpr)[0]  
    best_idx   = valid_idxs[np.argmax(tpr[valid_idxs])]

    chosen_thresh = thresholds[best_idx]
    chosen_tpr    = tpr[best_idx]
    chosen_fpr    = fpr[best_idx]

    print(f"To cap FPR at {chosen_fpr:.1%}, set threshold = {chosen_thresh:e}, "
        f"which yields TPR = {chosen_tpr:.1%}")

    min_tpr = 0.90
    valid_idxs = np.where(tpr >= min_tpr)[0]
    best_idx   = valid_idxs[np.argmin(fpr[valid_idxs])]

    chosen_thresh = thresholds[best_idx]
    chosen_tpr    = tpr[best_idx]
    chosen_fpr    = fpr[best_idx]

    print(f"To ensure TPR ≥ {chosen_tpr:.1%}, set threshold = {chosen_thresh:e}, "
        f"with FPR = {chosen_fpr:.1%}")

    percentile = 99
    threshold_at_pct = np.percentile(probs, percentile)
    print(f"Threshold at {percentile}th percentile = {threshold_at_pct:e}")

    # 3) Export to CSV
    roc_df = pd.DataFrame({
        'fpr': fpr,
        'tpr': tpr,
        'threshold': thresholds
    })
    roc_df.to_csv('roc_curve.csv', index=False)
    print("Wrote ROC curve data to roc_curve.csv")
    
    print(f"Training complete; best Val AUC = {best_auc:.4f}")


if __name__ == "__main__":
    main()
