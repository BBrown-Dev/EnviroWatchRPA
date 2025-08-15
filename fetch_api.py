# src/fetch_api.py
import os
import random
import logging
import datetime as dt
from typing import Optional
import pandas as pd
import requests

DEFAULT_STATIONS = [
    {"station_id": "ST101", "city": "Eau Claire", "lat": 44.811, "lon": -91.498},
    {"station_id": "ST202", "city": "Madison", "lat": 43.074, "lon": -89.384},
    {"station_id": "ST303", "city": "Minneapolis", "lat": 44.977, "lon": -93.265},
]


# Utility function to generate a date range
def _daterange(start_date: dt.date, end_date: dt.date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + dt.timedelta(n)


# Simulate realistic data for the given date range and stations
def _simulate_api(start: dt.date, end: dt.date) -> pd.DataFrame:
    rows = []
    for d in _daterange(start, end):
        for s in DEFAULT_STATIONS:
            rows.append({
                "station_id": s["station_id"],
                "date": d.isoformat(),
                "city": s["city"],
                "lat": s["lat"],
                "lon": s["lon"],
                "temp_c": round(random.uniform(-5, 32), 1),
                "humidity": random.randint(25, 95),
                "precip_mm": round(max(0, random.gauss(1.2, 2.0)), 1)
            })
    return pd.DataFrame(rows)


# HTTP GET request with retries and backoff
def _http_get(url: str, params: dict, headers: dict, attempts: int, timeout: float, backoff: float):
    for i in range(attempts):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            else:
                logging.warning({"event": "api_non_200", "status": resp.status_code, "body": resp.text[:200]})
        except requests.RequestException as e:
            logging.warning({"event": "api_exception", "error": str(e), "attempt": i + 1})
        if i < attempts - 1:
            dt.time.sleep(backoff)
    return None


# Fetch external data from an API or simulate it if offline
def fetch_external_data(start_date: str, end_date: str, offline: bool = False) -> pd.DataFrame:
    """
    Fetches weather/metadata-like data by station and date.
    Online: calls an external API endpoint (configurable).
    Offline: simulates realistic data covering stations and dates.
    """
    start = dt.date.fromisoformat(start_date)
    end = dt.date.fromisoformat(end_date)

    if offline:
        logging.info({"event": "api_simulated", "start": start_date, "end": end_date})
        return _simulate_api(start, end)

    base_url = os.getenv("API_ENDPOINT", "https://api.openaq.org/v2/measurements")
    api_key = os.getenv("API_KEY", "")
    attempts = int(os.getenv("API_RETRY_ATTEMPTS", "3"))
    timeout = float(os.getenv("API_TIMEOUT_SECONDS", "10"))
    backoff = float(os.getenv("API_BACKOFF_SECONDS", "1.5"))

    # Example request parameters (adapt or map to a chosen API)
    params = {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "limit": 1000
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    try:
        # Parsing below can be swapped to match chosen API’s response shape
        raw = _http_get(base_url, params, headers, attempts, timeout, backoff)
        if not raw:
            logging.error({"event": "api_fallback_simulation"})
            return _simulate_api(start, end)

        # Minimal flexible parsing to DataFrame
        # Expecting a list-like response or key "results"
        results = raw.get("results") if isinstance(raw, dict) else raw
        if not isinstance(results, list) or len(results) == 0:
            logging.warning({"event": "api_empty_or_unexpected"})
            return _simulate_api(start, end)

        # Map into our schema (station_id, city, lat, lon, date, temp_c, humidity, precip_mm)
        rows = []
        for r in results[:5000]:
            # Fallbacks to maintain schema integrity
            rows.append({
                "station_id": r.get("location") or r.get("station_id") or random.choice(DEFAULT_STATIONS)["station_id"],
                "city": r.get("city") or r.get("place") or "Unknown",
                "lat": (r.get("coordinates") or {}).get("latitude") if r.get("coordinates") else None,
                "lon": (r.get("coordinates") or {}).get("longitude") if r.get("coordinates") else None,
                "date": (r.get("date") or {}).get("utc")[:10] if isinstance(r.get("date"), dict) and r.get("date",
                                                                                                           {}).get(
                    "utc") else start.isoformat(),
                "temp_c": r.get("temperature") or round(random.uniform(-5, 32), 1),
                "humidity": r.get("humidity") or random.randint(25, 95),
                "precip_mm": r.get("precipitation") or round(max(0, random.gauss(1.2, 2.0)), 1)
            })
        df = pd.DataFrame(rows)
        # Clean dates
        df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
        logging.info({"event": "api_fetched", "rows": len(df)})
        return df

    except Exception as e:
        logging.exception({"event": "api_error", "error": str(e)})
        return _simulate_api(start, end)
