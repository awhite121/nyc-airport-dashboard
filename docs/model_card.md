# Model Card

## Model Purpose

Estimate NYC taxi trip duration and late-trip risk for Manhattan → JFK/LGA rides.

## Intended Use

Educational and portfolio project demonstrating applied ML, transportation analytics, regression, imbalanced classification, and decision thresholding.

## Not Intended For

Real-time dispatching or guaranteed airport arrival planning without live traffic, weather, and operational data.

## Data

NYC yellow taxi trip records and TLC taxi zone lookup. Cleaned to Manhattan pickups and JFK/LGA dropoffs.

## Features

Pre-trip or pickup-time features only: pickup zone, airport, pickup hour, pickup day of week, trip distance, passenger count, payment type.

## Evaluation

Regression: MAE, RMSE, R².  
Classification: precision, recall, F1, ROC-AUC, threshold tradeoff.

## Risks / Limitations

Single-month data, no weather, no traffic incidents, no live routing, airport-only use case, possible distribution drift.
