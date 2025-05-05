model = '' # could use XGBRegressor for now? 

def compute_risk(evt):
    features = evt.to_features_vector()
    return float(model.predict([features])[0])

# TODO: add all the risk logic and save best model in /risk_engine
