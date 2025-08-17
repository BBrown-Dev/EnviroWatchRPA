# This module provides functions to load local data sources for air quality and renewable energy share.

# fetch_db.py
import os
import sqlite3
import logging
import random
import datetime as dt
from typing import Optional, Tuple
import pandas as pd

DB_DEFAULT = "data/env.db"

# Utility function to ensure directory exists
def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

# Simulate realistic data for the given date range and stations
def _simulate_air_quality(start: dt.date, end: dt.date) -> pd.DataFrame:
    stations = ["ST101", "ST202", "ST303"]
    rows = []
    for d in (start + dt.timedelta(n) for n in range((end - start).days + 1)):
        for s in stations:
            rows.append({
                "station_id": s,
                "date": d.isoformat(),
                "aqi": random.randint(10, 200),
                "co2_ppm": round(random.uniform(350, 450), 1)
            })
    return pd.DataFrame(rows)

# Simulate renewable share data
def _simulate_renewables() -> pd.DataFrame:
    return pd.DataFrame([
        {"city": "Eau Claire", "renewable_share": 0.42},
        {"city": "Madison", "renewable_share": 0.51},
        {"city": "Minneapolis", "renewable_share": 0.47},
    ])

# Read data from SQLite database
def read_sqlite(db_path: str, table: str) -> pd.DataFrame:
    with sqlite3.connect(db_path) as con:
        return pd.read_sql_query(f"SELECT * FROM {table}", con)

# Load local sources for air quality and renewable share data
def load_local_sources(start_date: str, end_date: str,
                       db_path: Optional[str], offline: bool) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Always returns a valid (air_quality_df, renewable_share_df).
    Seeds air_quality table with simulated data if missing.
    """
    db = db_path or DB_DEFAULT
    _ensure_dir(os.path.dirname(db))

    # Try to read air_quality; if missing, simulate and persist
    try:
        aq = read_sqlite(db, "air_quality")
        logging.info({"event": "db_loaded", "rows": len(aq), "table": "air_quality"})
    except Exception as e:
        logging.warning({"event": "db_air_quality_missing", "error": str(e)})
        start = dt.date.fromisoformat(start_date)
        end = dt.date.fromisoformat(end_date)
        aq = _simulate_air_quality(start, end)
        with sqlite3.connect(db) as con:
            aq.to_sql("air_quality", con, if_exists="replace", index=False)
        logging.info({"event": "db_simulated_written", "rows": len(aq), "table": "air_quality"})

    # Renewable share: try CSV first, otherwise simulate + persist
    renew_csv = "data/renewable_share.csv"
    if os.path.exists(renew_csv):
        renew = pd.read_csv(renew_csv)
        logging.info({"event": "file_loaded", "rows": len(renew), "file": renew_csv})
    else:
        renew = _simulate_renewables()
        _ensure_dir(os.path.dirname(renew_csv))
        renew.to_csv(renew_csv, index=False)
        logging.info({"event": "file_simulated_written", "rows": len(renew), "file": renew_csv})

    return aq, renew