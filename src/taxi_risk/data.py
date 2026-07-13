from pathlib import Path
import pandas as pd

def load_processed(path: str | Path = "data/processed/taxi_clean_for_modeling.csv") -> pd.DataFrame:
    """Load cleaned Manhattan-to-airport taxi trips."""
    df = pd.read_csv(path, parse_dates=["tpep_pickup_datetime", "tpep_dropoff_datetime"])
    if "duration_min" not in df.columns and "trip_duration_min" in df.columns:
        df["duration_min"] = df["trip_duration_min"]
    return df

def load_zone_lookup(path: str | Path = "data/reference/taxi_zone_lookup.csv") -> pd.DataFrame:
    """Load TLC taxi zone lookup table."""
    return pd.read_csv(path)
