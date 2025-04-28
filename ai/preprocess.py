import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler, Normalizer

FEATURE_NAMES = []

def load_and_preprocess(
        csv_path="synthetic_logins.csv",
        include_fraud_as_feature=True,
        multitask=False # if multitask is true, function returns 2 targets: risk and fraud (remember to set include_fraud_as_feature to false)
        ):
    
    # load CSV
    df = pd.read_csv(csv_path)

    # rename target column
    df.rename(columns={"risk_score": "label"}, inplace=True)  # this should be whether the login attempt was fraudulent or not | should be float with softmax

    # parse timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # sort values so diffs and rolling windows make sense
    df.sort_values(["email", "timestamp"], inplace=True)

    # time since last login
    df["time_since_last"] = (
        df.groupby("email")["timestamp"]
        .diff()
        .dt.total_seconds()
        .div(3600)
    )

    # replace NaN (first login) with zero
    # df["time_since_last"].fillna(0, inplace=True)
    df["time_since_last"] = df["time_since_last"].fillna(0)

    # login frequency in past 1 h and 24 h
    def compute_freq(group):
        ts = group["timestamp"]
        freq_1h = []
        freq_24h = []
        for t in ts:
            freq_1h.append(((ts < t) & (ts >= t - pd.Timedelta(hours=1))).sum())
            freq_24h.append(((ts < t) & (ts >= t - pd.Timedelta(hours=24))).sum())
        return pd.DataFrame(
            {"freq_1h": freq_1h, "freq_24h": freq_24h},
            index=group.index
        )
    
    freq_df = df.groupby("email").apply(compute_freq)
    # drop the extra grouping index level
    freq_df.index = freq_df.index.droplevel(0)
    df = pd.concat([df, freq_df], axis=1)

    # extract hour and day-of-week (# parse timestamp into num features)
    # df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour # extract hour from timestamp
    df["dayofweek"] = df["timestamp"].dt.dayofweek # extract DoW from timestamp

    # drop raw timestamp
    df.drop(columns=["timestamp"], inplace=True)

    # convert boolean or categorical features
    df["login_result"] = df["login_result"].astype(int) 
    df["fraud"] = df["fraud"].astype(int)

    """
    One-hot encoding is a technique to convert categorical data into a numerical format that can be used by machine learning algorithms.
    Instead of representing a categorical variable with a single column (which would imply an ordinal relationship or magnitude), one-hot encoding creates a new binary (0 or 1) column for each unique category.
    """

    # one-hot encode country, region, city (drop origin)
    ohe = OneHotEncoder(sparse_output=False, drop="first")
    cat_cols = ["country", "region", "city"]
    cat_data = ohe.fit_transform(df[cat_cols])
    cat_df = pd.DataFrame(cat_data, columns=ohe.get_feature_names_out(cat_cols))
    df = pd.concat([df.drop(columns=cat_cols), cat_df], axis=1)

    # TODO: consider word embedding for city/country/region

    # drop high-cardinality (free) text fields (not useful for tabular NN, not directly usable)
    df.drop(columns=["email", "ip_address", "user_agent", "device_fingerprint"], inplace=True)

    # TODO: consider word embedding for the above

    # split into X and y
    # X = df.drop(columns=["label"])
    # y = df["label"]

    # split targets
    y_risk = df["label"].values / 100.0 # normalize to [0,1]

    if multitask:
        y_fraud = df["fraud"].values

    df.drop(columns=["label"], inplace=True)
    if not include_fraud_as_feature:
        df.drop(columns=["fraud"], inplace=True)


    # scale numeric features
    # scaler = StandardScaler()
    # X_scaled = scaler.fit_transform(X)

    # prepare features (X) and scale
    # feature_cols = [c for c in df.columns if c not in (["fraud"] if multitask else [])]
    feature_cols = df.columns.tolist()

    global FEATURE_NAMES
    FEATURE_NAMES = feature_cols.copy()
    
    X = df[feature_cols].copy()
    scaler = Normalizer()
    X_scaled = scaler.fit_transform(X)

    # train/test split into NumPy arrays for the model
    # X_train, X_test, y_train, y_test = train_test_split(
    #     X_scaled, y.values, test_size=0.2, random_state=42
    # )
    # return X_train, X_test, y_train, y_test

    # train/test split
    if multitask:
        X_train, X_test, r_train, r_test, f_train, f_test = train_test_split(
            X_scaled, y_risk, y_fraud, test_size=0.2, random_state=42
        )
        return X_train, X_test, r_train, r_test, f_train, f_test
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_risk, test_size=0.2, random_state=42
        )
        return X_train, X_test, y_train, y_test

# allow importing directly for single‑task risk regression
X_train, X_test, y_train, y_test = load_and_preprocess()

if __name__ == "__main__":
    load_and_preprocess()
    print('Size of X_train', X_train.shape, '\nSize of y_train:', y_train.shape)
    print(X_train[:10])
