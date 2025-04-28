import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt

df = pd.read_csv("roc_curve.csv")
fpr = df['fpr']
tpr = df['tpr']
thresholds = df['threshold']
roc_auc = auc(fpr, tpr)

plt.figure()
plt.plot(df['fpr'], df['tpr'], label=f'AUC = {roc_auc:.3f}')
plt.plot([0,1],[0,1],'--', color='gray')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve')
plt.legend()
plt.show()



j_scores = tpr - fpr
ix = np.argmax(j_scores)
# optimal_threshold = thresholds[ix]
opt_prob_thresh = thresholds[ix]
# print(f"Best threshold by Youden J: {optimal_threshold:.4f}  (TPR={tpr[ix]:.3f}, FPR={fpr[ix]:.3f})")
print(f"Youden-optimal probability threshold: {opt_prob_thresh:.6f} "
      f"(TPR={tpr[ix]:.3f}, FPR={fpr[ix]:.3f})")

max_fpr = 0.05
valid = np.where(fpr <= max_fpr)[0]
idx = valid[np.argmax(tpr[valid])]
# threshold_at_1pct_fpr = thresholds[idx]
fpr01 = fpr[idx]; tpr01 = tpr[idx]; prob01 = thresholds[idx]
# print(f"Threshold for FPR≤1%: {threshold_at_1pct_fpr:.4f}  (TPR={tpr[idx]:.3f})")
print(f"Threshold for FPR≤1%: {prob01:.6f} (TPR={tpr01:.3f})")

# # already have fpr, tpr, thresholds from roc_curve on probs
# max_fpr = 0.05                   # 5% max false positives
# valid_idxs = np.where(fpr <= max_fpr)[0]  
# best_idx   = valid_idxs[np.argmax(tpr[valid_idxs])]

# chosen_thresh = thresholds[best_idx]
# chosen_tpr    = tpr[best_idx]
# chosen_fpr    = fpr[best_idx]

# print(f"To cap FPR at {chosen_fpr:.1%}, set threshold = {chosen_thresh:e}, "
#       f"which yields TPR = {chosen_tpr:.1%}")

# min_tpr = 0.90
# valid_idxs = np.where(tpr >= min_tpr)[0]
# best_idx   = valid_idxs[np.argmin(fpr[valid_idxs])]

# chosen_thresh = thresholds[best_idx]
# chosen_tpr    = tpr[best_idx]
# chosen_fpr    = fpr[best_idx]

# print(f"To ensure TPR ≥ {chosen_tpr:.1%}, set threshold = {chosen_thresh:e}, "
#       f"with FPR = {chosen_fpr:.1%}")

# percentile = 99
# threshold_at_pct = np.percentile(probs, percentile)
# print(f"Threshold at {percentile}th percentile = {threshold_at_pct:e}")


plt.plot(fpr, tpr, label=f'AUC={roc_auc:.3f}')
plt.scatter(fpr[ix], tpr[ix], color='red', label=f'Youden@{opt_prob_thresh:.3f}')
plt.scatter(fpr[idx], tpr[idx], color='green',
            label=f'FPR1%@{prob01:.3f}')
plt.plot([0,1],[0,1],'--', color='gray')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.legend()
plt.show()

# load file
df = pd.read_csv("inference_output.csv")

# histogram of risk probabilities
plt.figure()
plt.hist(df['risk_prob'], bins=50)
plt.title('Distribution of Risk Scores')
plt.xlabel('Risk Probability')
plt.ylabel('Count')
plt.tight_layout()
plt.show()

# histogram of actual risk
plt.figure()
plt.hist(df['label'], bins=50)
plt.title('Distribution of Risk Scores')
plt.xlabel('Actual Risk')
plt.ylabel('Count')
plt.tight_layout()
plt.show()

# bar chart: low vs high risk (threshold 0.5)
threshold = 2.93e-08
counts = [
    (df['risk_prob'] < threshold).sum(),
    (df['risk_prob'] >= threshold).sum()
]
labels = [f'Low risk (<{threshold})', f'High risk (>={threshold})']

plt.figure()
plt.bar(labels, counts)
plt.title('Counts of Low vs High Risk Logins')
plt.ylabel('Number of Logins')
plt.tight_layout()
plt.show()

