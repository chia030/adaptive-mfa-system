import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from preprocess import X_train, y_train, X_test, y_test
# from ai.preprocess import load_and_preprocess
import numpy as np

y_train = y_train * 100
y_test  = y_test  * 100

# dataset + dataloader
class LoginDataset(Dataset):
    def __init__(self, X, y):
        # X and y are numpy arrays after preprocessing
        # self.X = torch.tensor(X.values, dtype=torch.float32)
        # self.y = torch.tensor(y.values, dtype=torch.float32).unsqueeze(1)
        self.X = torch.from_numpy(X).float()
        self.y = torch.from_numpy(y).float().unsqueeze(1)
    
    def __len__(self):
        return  len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

train_loader = DataLoader(LoginDataset(X_train, y_train), batch_size=32, shuffle=True) # why shuffle=true? maybe bad idea when multiple failed attempts | batch size was 64
val_loader = DataLoader(LoginDataset(X_test, y_test), batch_size=32) # batch size was 64

#TODO: look into softmax activation function

# model definition
# TODO: consider adding more layers or making them biggers if it's not good enough
class RiskModel(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            # layer 1
            nn.Linear(input_dim, 128), # linear layer, 64 neurons
            nn.BatchNorm1d(128), # batch normalization
            nn.ReLU(), # takes input from layer and decide whether to activate the perceptron or not
            nn.Dropout(0.3), # (was) 30 % chance output is ignored
            # layer 2
            nn.Linear(128, 64), # was 64, 32
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),
            # layer 3
            nn.Linear(64,32),
            nn.BatchNorm1d(32),
            nn.ReLU(), # try turning into softmax (output -> probability)
            nn.Dropout(0.2),
            # final output
            nn.Linear(32, 1)  # regression risk score | was 32
        )
    def forward(self, x): # inference
        return self.net(x)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = RiskModel(input_dim=X_train.shape[1]).to(device)

# optimizer, loss and early stopping params
optimizer = optim.Adam(model.parameters(), lr=1e-4, weight_decay=1e-5) # math function defining how to calculate loss / learning rate = 0.001 (steps taken to get to a minimum) | was 1e-5
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', factor=0.5, patience=2)
# loss_fn = nn.MSELoss() # loss function
loss_fn = nn.SmoothL1Loss()
best_val_loss = np.inf
patience = 100 # was 3
epochs_no_improve = 0

# training + validation loop with early stopping
num_epochs = 300
for epoch in range(1, num_epochs + 1):
    # —— training —— #
    model.train()
    train_losses = []
    for xb, yb in train_loader:
        xb, yb = xb.to(device), yb.to(device)
        preds = model(xb) # give prediction X to model
        loss = loss_fn(preds, yb) # compare to y and calc loss
        optimizer.zero_grad() # reset gradients (so they dont carry over into next epoch)
        loss.backward() # learning (backward propagation, calculating gradient)
        optimizer.step() # apply to model
        train_losses.append(loss.item())
    
    # —— validation —— #
    model.eval()
    val_losses = []
    with torch.no_grad(): # disable gradients so it goes faster
        for xb, yb in val_loader:
            xb, yb = xb.to(device), yb.to(device)
            preds = model(xb)
            val_losses.append(loss_fn(preds, yb).item())
    
    avg_train_loss = np.mean(train_losses)
    avg_val_loss = np.mean(val_losses)
    print(f"Epoch {epoch:02d}: train_loss = {avg_train_loss:.4f}, val_loss = {avg_val_loss:.4f}")

    # —— early stopping check —— #
    if avg_val_loss < best_val_loss:
        best_val_loss = avg_val_loss
        epochs_no_improve = 0
        # save best model
        torch.save(model.state_dict(), "./risk_model_best.pth")
    else:
        epochs_no_improve += 1
        if epochs_no_improve >= patience:
            print(f"Validation loss did not improve for {patience} epochs. Stopping early.")
            break

# final save (optional)
torch.save(model.state_dict(), "./risk_model_last.pth")
