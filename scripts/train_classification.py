from taxi_risk.data import load_processed
from taxi_risk.modeling import DEFAULT_FEATURES, make_late_risk_model
from taxi_risk.metrics import classification_metrics
import pandas as pd

df = load_processed().sort_values("tpep_pickup_datetime")
if "is_late" not in df.columns:
    raise ValueError("Processed dataset must include is_late label. Run scripts/make_dataset.py first.")

split = int(len(df) * 0.8)
X_train, X_test = df[DEFAULT_FEATURES].iloc[:split], df[DEFAULT_FEATURES].iloc[split:]
y_train, y_test = df["is_late"].iloc[:split], df["is_late"].iloc[split:]

model = make_late_risk_model("random_forest")
model.fit(X_train, y_train)
proba = model.predict_proba(X_test)[:, 1]
results = pd.DataFrame([classification_metrics(y_test, proba, t) for t in [0.5, 0.4, 0.35, 0.3]])
print(results.to_string(index=False))
