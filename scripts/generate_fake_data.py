# Script to generate synthetic environmental data for air quality and renewable energy share.
# This is useful for offline testing and development without relying on live APIs or databases.

import os
import sqlite3
import random
import datetime as dt
import pandas as pd
from faker import Faker

# Ensure data directory exists
os.makedirs("../data", exist_ok=True)
fake = Faker()

# Generate synthetic air quality data
def generate_air_quality(rows_per_station_per_day=1, days_back=30):
    stations = ["ST101", "ST202", "ST303"]
    end = dt.date.today()
    start = end - dt.timedelta(days=days_back)
    rows = []
    for d in (start + dt.timedelta(n) for n in range(days_back + 1)):
        for s in stations:
            for _ in range(rows_per_station_per_day):
                rows.append({
                    "station_id": s,
                    "date": d.isoformat(),
                    "aqi": random.randint(10, 200),
                    "co2_ppm": round(random.uniform(350, 450), 1)
                })
    return pd.DataFrame(rows)

# Main function to create synthetic database and CSV
def main():
    con = sqlite3.connect("../data/env.db")
    aq = generate_air_quality()
    aq.to_sql("air_quality", con, if_exists="replace", index=False)
    con.close()

    renew = pd.DataFrame([
        {"city": "Eau Claire", "renewable_share": 0.42},
        {"city": "Madison", "renewable_share": 0.51},
        {"city": "Minneapolis", "renewable_share": 0.47},
    ])
    renew.to_csv("../data/renewable_share.csv", index=False)
    print("✅ synthetic database saved to data/env.db and renewable_share.csv")

if __name__ == "__main__":
    main()