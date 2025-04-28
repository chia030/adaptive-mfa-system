import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib


# def main(args):
def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    # Extract features from dataset:

    # 1. Failures in past 60 min (from "failed_login" flag)
    # load and parse timestamps
    # df = pd.read_csv(args.input, parse_dates=['Login Timestamp'])
    df = df.sort_values(['User ID', 'Login Timestamp'])
    # get failures from last hour
    # derive failed_login from login_successful (True/False → 0/1 inverted)
    df['failed_login'] = (~df['Login Successful']).astype(int)
    df.set_index('Login Timestamp', inplace=True)
    df['fail_60m'] = (
        df.groupby('User ID')['failed_login']
        .rolling('60min')
        .sum()
        .reset_index(level=0, drop=True)
    )
    df.reset_index(inplace=True)

    # 2. 'Login Successful' historical context (Successes in past 60 min)
    df.set_index('Login Timestamp', inplace=True)
    df['succ_60m'] = (
        df.groupby('User ID')['Login Successful']
        .rolling('60min')
        .sum()
        .reset_index(level=0, drop=True)
    )
    df.reset_index(inplace=True)

    # 3. Hour-of-day deviation (from timestamp)
    df['hour'] = df['Login Timestamp'].dt.hour
    user_hour_mean = df.groupby('User ID')['hour'].transform('mean')
    df['hour_dev'] = (df['hour'] - user_hour_mean).abs()

    # 4. Device-unfamiliar (compare device_id to user's recent device)
    df['device_fp'] = df['User Agent String']
    df['prev_device_fp'] = df.groupby('User ID')['device_fp'].shift(1)
    df['device_unfamiliar'] = (df['device_fp'] != df['prev_device_fp']).astype(int)
    df.drop(columns=['prev_device_fp'], inplace=True)

    # 5. Country/Region change since last login
    # country change flag
    df['prev_country'] = df.groupby('User ID')['Country'].shift(1)
    df['country_change'] = (df['Country'] != df['prev_country']).astype(int)
    df.drop(columns=['prev_country'], inplace=True)
    # region change flag
    df['prev_region'] = df.groupby('User ID')['Region'].shift(1)
    df['region_change'] = (df['Region'] != df['prev_region']).astype(int)
    df.drop(columns=['prev_region'], inplace=True)

    # 6. Impossible travel
    df = df.sort_values(['User ID', 'Login Timestamp'])
    df['prev_timestamp'] = df.groupby('User ID')['Login Timestamp'].shift(1)
    # calculate time difference
    df['time_diff_hours'] = (
        df['Login Timestamp'] - df['prev_timestamp']
    ).dt.total_seconds() / 3600
    # threshold for impossible travel = 1 hour
    threshold_hours = 1.0
    df['impossible_travel'] = (
        (df['country_change'] == 1) &
        (df['time_diff_hours'] < threshold_hours)
    ).astype(int)

    # 7. IP-reputation
    df['ip_attack_rep'] = df['Is Attack IP'].astype(int)
    
    # select features & label
    features = [
        'fail_60m', # rolling count of failures
        'succ_60m', # rolling count of successes
        'hour_dev', # time-of-day deviation 
        'device_unfamiliar', # new device flag
        'country_change',
        'region_change',
        'impossible_travel', # new country <1h from last login
        'ip_attack_rep' # using Is Attack IP
    ]

    # 8. Is Account Takeover (Fraud=True/False) as label
    # rename target column
    df.rename(columns={"Is Account Takeover": "label"}, inplace=True)
    # convert True/False → 1/0
    df['label'] = df['label'].astype(int)

    global FEATURES
    FEATURES = features.copy()

    global NUM_FEATURES
    NUM_FEATURES = [
        'fail_60m',
        'succ_60m',
        'hour_dev'
    ]

    global BIN_FEATURES
    BIN_FEATURES = [
        'device_unfamiliar',
        'country_change',
        'region_change',
        'impossible_travel',
        'ip_attack_rep'
    ]

    out = df[features + ['label']].fillna(0)

    print(f"{out}")
    
    # write to csv
    out.to_csv("features.csv", index=False)
    print(f"Saved {len(out)} rows with features to features.csv")
    return out

def build_preprocessor(numeric_features, binary_features):
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_features),
            ('bin', 'passthrough', binary_features)
        ]
    )
    return preprocessor

def load_and_preprocess(csv_path="rba-ds-sample.csv"):
    # load data
    df = pd.read_csv(csv_path, parse_dates=['Login Timestamp'])

    # extract feautures
    df = extract_features(df)

    # for inference
    # df.to_csv("inference-data.csv", index=False)

    # define X, y, and train/test split
    X = df[FEATURES]
    y = df['label'].astype(int)

    X_train, X_test, y_train, y_test, = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        shuffle=True,
        stratify=y # <— preserves the 0/1 ratio across train & test
    )

    # build and fit preprocessing + model
    preprocessor = build_preprocessor(NUM_FEATURES, BIN_FEATURES)
    pipeline = Pipeline(steps=[
        ('preproc', preprocessor),
        # other models here
    ])
    # fit only the preprocessor
    pipeline.fit(X_train)

    # transform and save outputs
    X_train_proc = pipeline.transform(X_train)
    X_test_proc = pipeline.transform(X_test)
    
    # reassemble into dfs
    train_out = pd.DataFrame(X_train_proc, columns=FEATURES)
    train_out['label'] = y_train.reset_index(drop=True)

    test_out = pd.DataFrame(X_test_proc, columns=FEATURES)
    test_out['label'] = y_test.reset_index(drop=True)

    train_out.to_csv("train_output.csv", index=False)
    test_out.to_csv("test_output.csv", index=False)

    print("Processed data saved to train_output.csv and test_output.csv")
    print('Size of X_train', X_train.shape, '\nSize of y_train:', y_train.shape)
    print(X_train[:10])

    print("Train label distribution:", np.bincount(y_train))
    print("Test  label distribution:", np.bincount(y_test))


    preprocessor = pipeline.named_steps['preproc']
    joblib.dump(preprocessor, 'preprocessor.joblib')


if __name__ == "__main__":
    load_and_preprocess()
    