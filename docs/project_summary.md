# Project Summary

This project predicts NYC airport taxi travel time and late-trip risk for Manhattan pickups to JFK or LaGuardia.

## Business Question

Can historical taxi data estimate both expected trip duration and the probability that a ride will be unusually slow?

## Final Product Concept

An Airport Taxi Timing Advisor:

- predicts expected trip duration,
- estimates late-trip probability,
- recommends a buffer depending on the user's risk tolerance.

## What I Built

- Cleaned raw NYC taxi data.
- Joined pickup/dropoff zone metadata.
- Filtered to Manhattan → JFK/LGA trips.
- Engineered time, airport, distance, and location features.
- Built regression models for trip duration.
- Built classification models for late risk.
- Tuned classification thresholds for traveler vs. operations use cases.
- Created buffer-time logic that translates model output into action.

## Results

- Clean modeling dataset: 43,079 rides.
- Duration MAE improved from 13.06 minutes to ~5.6 minutes.
- CatBoost achieved ROC-AUC ~0.725 for late-risk prediction.
- Risk-averse threshold caught ~82.6% of late trips.
