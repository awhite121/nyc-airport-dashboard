import numpy as np
import pandas as pd

AIRPORT_ZONE_IDS = {"JFK": 132, "LGA": 138}

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add pickup hour and day-of-week features."""
    out = df.copy()
    out["tpep_pickup_datetime"] = pd.to_datetime(out["tpep_pickup_datetime"], errors="coerce")
    out["tpep_dropoff_datetime"] = pd.to_datetime(out["tpep_dropoff_datetime"], errors="coerce")
    out["duration_min"] = (out["tpep_dropoff_datetime"] - out["tpep_pickup_datetime"]).dt.total_seconds() / 60
    out["pickup_hour"] = out["tpep_pickup_datetime"].dt.hour
    out["pickup_dow"] = out["tpep_pickup_datetime"].dt.dayofweek
    return out

def filter_airport_trips(df: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
    """Filter to Manhattan pickups and JFK/LGA dropoffs."""
    out = df.merge(zones[["LocationID", "Borough", "Zone"]], left_on="PULocationID", right_on="LocationID", how="left")
    out = out.rename(columns={"Borough": "PU_Borough", "Zone": "PU_Zone"}).drop(columns=["LocationID"])
    out = out.merge(zones[["LocationID", "Borough", "Zone"]], left_on="DOLocationID", right_on="LocationID", how="left")
    out = out.rename(columns={"Borough": "DO_Borough", "Zone": "DO_Zone"}).drop(columns=["LocationID"])
    is_manhattan = out["PU_Borough"].eq("Manhattan")
    is_airport = out["DOLocationID"].isin(AIRPORT_ZONE_IDS.values())
    out = out[is_manhattan & is_airport].copy()
    out["airport"] = np.where(out["DOLocationID"].eq(AIRPORT_ZONE_IDS["JFK"]), "JFK", "LGA")
    return out

def remove_implausible_trips(df: pd.DataFrame, min_minutes: float = 3, max_minutes: float = 180) -> pd.DataFrame:
    """Remove impossible or extremely unusual trips for modeling stability."""
    mask = (
        df["duration_min"].notna()
        & df["trip_distance"].gt(0)
        & df["duration_min"].between(min_minutes, max_minutes)
        & df["passenger_count"].ge(1)
    )
    return df.loc[mask].copy()

def add_late_label(df: pd.DataFrame, multiplier: float = 1.2) -> pd.DataFrame:
    """Label late trips as > multiplier times typical duration for airport/hour/day group."""
    out = df.copy()
    group_cols = ["airport", "pickup_hour", "pickup_dow"]
    med = out.groupby(group_cols)["duration_min"].median().rename("typical_duration_min").reset_index()
    out = out.drop(columns=["typical_duration_min"], errors="ignore").merge(med, on=group_cols, how="left")
    out["is_late"] = (out["duration_min"] > multiplier * out["typical_duration_min"]).astype(int)
    return out
