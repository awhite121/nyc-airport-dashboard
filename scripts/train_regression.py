from taxi_risk.data import load_processed
from taxi_risk.modeling import DEFAULT_FEATURES, make_duration_model
from taxi_risk.metrics import regression_metrics
import numpy as np

df = load_processed().sort_values("tpep_pickup_datetime")
split = int(len(df) * 0.8)
X_train, X_test = df[DEFAULT_FEATURES].iloc[:split], df[DEFAULT_FEATURES].iloc[split:]
y_train, y_test = df["duration_min"].iloc[:split], df["duration_min"].iloc[split:]

baseline = np.full_like(y_test, y_train.median(), dtype=float)
print("Baseline:", regression_metrics(y_test, baseline))

model = make_duration_model("random_forest")
model.fit(X_train, y_train)
preds = model.predict(X_test)
print("Random Forest:", regression_metrics(y_test, preds))
