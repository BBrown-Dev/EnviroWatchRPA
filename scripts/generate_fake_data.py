# generate_fake_data.py
# Synthetic generators for offline mode

import pandas as pd
import numpy as np
import random

def generate_fake_air_quality(stations, dates):
    """Generate fake air quality data for each station/date."""
    rows = []
    for stn in stations:
        for dt in dates:
            # Example metadata map (optional)
            station_meta = {
                'ST101': ('Eau Claire', 44.8113, -91.4985),
                'ST102': ('Madison', 43.0731, -89.4012),
                'ST103': ('Minneapolis', 44.9778, -93.2650),
            }
            city, lat, lon = station_meta.get(stn, ('Unknown', np.nan, np.nan))
            rows.append({
                "station_id": stn,
                "date": dt,
                "city": city,
                "lat": lat,
                "lon": lon,
                "pm25": round(random.uniform(5, 80), 1),
                "pm10": round(random.uniform(10, 150), 1),
                "aqi": round(random.uniform(20, 200), 1)
            })
    return pd.DataFrame(rows)

def generate_fake_weather(air_quality_df):
    """Generate complete weather data for every station/date in air_quality_df."""
    station_meta = {
        'ST101': ('Eau Claire', 44.8113, -91.4985),
        'ST102': ('Madison', 43.0731, -89.4012),
        'ST103': ('Minneapolis', 44.9778, -93.2650),
    }

    rows = []
    for _, row in air_quality_df.iterrows():
        city, lat, lon = station_meta.get(row['station_id'], ('Unknown', np.nan, np.nan))
        temp_c = round(np.random.uniform(10, 30), 1)
        rows.append({
            'station_id': row['station_id'],
            'date': row['date'],
            'city': city,
            'lat': lat,
            'lon': lon,
            'temp_c': temp_c,
            'temp_f': round(temp_c * 9/5 + 32, 1),  # Fahrenheit added for schema parity
            'humidity': round(np.random.uniform(40, 90), 1),
            'precip_mm': round(np.random.uniform(0, 5), 2)
        })
    return pd.DataFrame(rows)

def generate_fake_renewable(cities):
    """Generate fake renewable share data per city."""
    return pd.DataFrame([{
        "city": city,
        "renewable_share": round(random.uniform(10, 90), 1)
    } for city in cities])