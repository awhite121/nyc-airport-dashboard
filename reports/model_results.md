# Model Results

## Regression

| Model | Test MAE | Test RMSE | Test R² |
|---|---:|---:|---:|
| Historical median baseline | 13.06 | 16.32 | — |
| Linear Regression | 6.62 | 9.09 | 0.68 |
| XGBoost tuned | 5.61 | 7.66 | 0.773 |
| Random Forest tuned | 5.60 | 7.60 | 0.776 |

## Classification

Late = duration > 120% of typical duration by airport × pickup hour × day-of-week.

| Model / Setting | Threshold | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Always on-time baseline | — | — | 0.000 | 0.000 | — |
| CatBoost balanced | 0.50 | 0.299 | 0.662 | 0.412 | 0.725 |
| CatBoost traveler-safe | 0.40 | 0.257 | 0.826 | 0.392 | 0.725 |
| CatBoost high recall | 0.30 | 0.226 | 0.915 | 0.362 | 0.725 |

## Decision Takeaway

The model is most valuable when treated as a decision-support system, not just a prediction model. The threshold changes depending on whether the stakeholder wants high recall for traveler safety or higher precision for operations monitoring.
