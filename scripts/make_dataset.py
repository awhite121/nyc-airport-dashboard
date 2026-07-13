"""Create a cleaned Manhattan -> JFK/LGA airport trip dataset from raw TLC taxi data."""
from pathlib import Path
import argparse
import pandas as pd
from taxi_risk.features import add_time_features, filter_airport_trips, remove_implausible_trips, add_late_label

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="data/raw/taxi_data.csv")
    parser.add_argument("--zones", default="data/reference/taxi_zone_lookup.csv")
    parser.add_argument("--out", default="data/processed/taxi_clean_for_modeling.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.raw, low_memory=False)
    zones = pd.read_csv(args.zones)
    df = add_time_features(df)
    df = filter_airport_trips(df, zones)
    df = remove_implausible_trips(df)
    df = add_late_label(df)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df):,} cleaned trips to {args.out}")

if __name__ == "__main__":
    main()
