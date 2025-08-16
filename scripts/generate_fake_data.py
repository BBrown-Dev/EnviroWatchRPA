# Script to generate synthetic environmental data for demo purposes.
# It creates a SQLite database with air quality and weather data,
# and a CSV file with renewable energy share data.

import os
import sqlite3
import numpy as np
import pandas as pd
import datetime as dt

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
os.makedirs(DATA_DIR, exist_ok=True)

def generate_air_quality(rows_per_station_per_day=1, days_back=30):
    """Generate simulated AQI and CO₂ readings per station/day."""
    stations = ["ST101", "ST202", "ST303"]
    dates = pd.date_range(end=dt.date.today(), periods=days_back + 1)
    station_ids = np.repeat(stations, len(dates) * rows_per_station_per_day)
    dates = np.tile(dates, len(stations) * rows_per_station_per_day)
    aqi = np.random.randint(10, 200, size=len(station_ids))
    co2_ppm = np.round(np.random.uniform(350, 450, size=len(station_ids)), 1)
    return pd.DataFrame({"station_id": station_ids, "date": dates, "aqi": aqi, "co2_ppm": co2_ppm})

def c_to_f(c):
    """Convert Celsius to Fahrenheit."""
    return (c * 9 / 5) + 32

def generate_weather(days_back=30):
    """Generate simulated daily weather with dual temperature units."""
    stations = [
        {"station_id": "ST101", "city": "Eau Claire", "lat": 44.811, "lon": -91.498},
        {"station_id": "ST202", "city": "Madison", "lat": 43.074, "lon": -89.384},
        {"station_id": "ST303", "city": "Minneapolis", "lat": 44.977, "lon": -93.265},
    ]
    dates = pd.date_range(end=dt.date.today(), periods=days_back + 1)
    station_data = pd.DataFrame(stations).repeat(len(dates)).reset_index(drop=True)
    station_data["date"] = np.tile(dates, len(stations))
    station_data["temp_c"] = np.round(np.random.uniform(-5, 32, size=len(station_data)), 1)
    station_data["temp_f"] = c_to_f(station_data["temp_c"])
    station_data["humidity"] = np.random.randint(25, 95, size=len(station_data))
    station_data["precip_mm"] = np.round(np.maximum(0, np.random.normal(1.2, 2.0, size=len(station_data))), 1)
    return station_data

def generate_renewable_share():
    """Generate static renewable share CSV for demo purposes."""
    return pd.DataFrame([
        {"city": "Eau Claire", "renewable_share": 0.42},
        {"city": "Madison", "renewable_share": 0.51},
        {"city": "Minneapolis", "renewable_share": 0.47},
    ])

def main():
    """Main function to generate and save synthetic data."""
    db_path = os.path.join(DATA_DIR, "env.db")
    with sqlite3.connect(db_path) as con:
        aq = generate_air_quality()
        aq.to_sql("air_quality", con, if_exists="replace", index=False, chunksize=1000)

        weather = generate_weather()
        con.execute("""
        CREATE TABLE IF NOT EXISTS weather_by_station (
            station_id TEXT NOT NULL,
            date TEXT NOT NULL,
            city TEXT,
            lat REAL,
            lon REAL,
            temp_c REAL,
            temp_f REAL,
            humidity REAL,
            precip_mm REAL,
            PRIMARY KEY (station_id, date)
        );
        """)
        weather.to_sql("weather_by_station", con, if_exists="replace", index=False, chunksize=1000)

    renew = generate_renewable_share()
    renew.to_csv(os.path.join(DATA_DIR, "renewable_share.csv"), index=False)

    print(f"✅ Synthetic data saved to {db_path} and renewable_share.csv")

if __name__ == "__main__":
    main()