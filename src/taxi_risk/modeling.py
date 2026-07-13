from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression

DEFAULT_FEATURES = ["trip_distance", "passenger_count", "pickup_hour", "pickup_dow", "payment_type", "airport", "PULocationID"]
CAT_COLS = ["airport", "PULocationID", "payment_type"]
NUM_COLS = ["trip_distance", "passenger_count", "pickup_hour", "pickup_dow"]

def make_preprocessor():
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS),
        ("num", "passthrough", NUM_COLS),
    ])

def make_duration_model(model_type: str = "random_forest") -> Pipeline:
    if model_type == "linear":
        model = LinearRegression()
    elif model_type == "random_forest":
        model = RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=42, n_jobs=-1)
    else:
        raise ValueError("model_type must be 'linear' or 'random_forest'")
    return Pipeline([("preprocess", make_preprocessor()), ("model", model)])

def make_late_risk_model(model_type: str = "random_forest") -> Pipeline:
    if model_type == "logistic":
        model = LogisticRegression(max_iter=1000, class_weight="balanced")
    elif model_type == "random_forest":
        model = RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced", random_state=42, n_jobs=-1)
    else:
        raise ValueError("model_type must be 'logistic' or 'random_forest'")
    return Pipeline([("preprocess", make_preprocessor()), ("model", model)])
