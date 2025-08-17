# EcoAnalytics EnviroWatchRPA ETL Pipeline
# Orchestrates ETL for environmental analytics, with guaranteed DB seeding from fetch_db

import argparse
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import date, timedelta

from dotenv import load_dotenv

from fetch_api import fetch_external_data
from fetch_db import load_local_sources
from transform import clean_and_join, add_temp_fahrenheit, compute_kpis

# Logging setup
def setup_logging(level: str = "INFO"):
    os.makedirs("data/logs", exist_ok=True)
    handler = RotatingFileHandler("data/logs/app.log", maxBytes=2_000_000, backupCount=5)
    formatter = logging.Formatter(fmt='{"time":"%(asctime)s","level":"%(levelname)s","message":%(message)s}')
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(handler)

class JsonLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        if isinstance(msg, dict):
            return json.dumps(msg), kwargs
        return json.dumps({"event": "log", "message": str(msg)}), kwargs

# CLI arguments
def parse_args():
    p = argparse.ArgumentParser(description="EnviroWatchRPA - EcoAnalytics ETL Pipeline")
    p.add_argument("--start-date", type=str, help="ISO date, e.g., 2025-07-01")
    p.add_argument("--end-date", type=str, help="ISO date, e.g., 2025-07-31")
    p.add_argument("--offline", action="store_true", help="Use synthetic data instead of live API/DB")
    p.add_argument("--db-path", type=str, help="Path to SQLite DB")
    p.add_argument("--output", type=str, default="data/final_enriched.parquet", help="Parquet output path")
    p.add_argument("--log-level", type=str, help="DEBUG, INFO, WARNING, ERROR")
    p.add_argument("--include-fahrenheit", action="store_true", help="Add Fahrenheit column to output")
    return p.parse_args()

# Main function
def main():
    load_dotenv()
    args = parse_args()

    # Logging
    log_level = args.log_level or os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level)
    log = JsonLoggerAdapter(logging.getLogger(__name__), {})

    # Date range
    if args.start_date and args.end_date:
        start_date, end_date = args.start_date, args.end_date
    else:
        end = date.today()
        start = end - timedelta(days=13)
        start_date, end_date = start.isoformat(), end.isoformat()

    log.info({
        "event": "run_started",
        "offline": args.offline,
        "start_date": start_date,
        "end_date": end_date,
        "include_fahrenheit": args.include_fahrenheit
    })
    print(f"[RUN CONFIG] offline={args.offline} db_path={args.db_path or 'data/env.db'}")

    try:
        # API data source
        if args.offline:
            from scripts.generate_fake_data import (
                generate_fake_air_quality,  # Not strictly needed here anymore
                generate_fake_weather,
                generate_fake_renewable,
            )
            # Simulate API weather data only — DB seeding handled in fetch_db
            stations = [s.strip() for s in os.getenv("STATIONS", "ST101,ST102,ST103").split(",") if s.strip()]
            from datetime import datetime as dtm
            s = dtm.fromisoformat(start_date).date()
            e = dtm.fromisoformat(end_date).date()
            dates = [(s + timedelta(days=i)).isoformat() for i in range((e - s).days + 1)]

            api_df = generate_fake_weather(generate_fake_air_quality(stations, dates))
            renew_df_api = generate_fake_renewable(sorted(api_df["city"].dropna().unique().tolist()))
        else:
            api_df = fetch_external_data(start_date, end_date, offline=False)
            renew_df_api = None  # from local_sources instead

        # Local sources (always returns a valid air_quality + renewables)
        aq_df, renew_df_local = load_local_sources(start_date, end_date, args.db_path, offline=args.offline)

        # Pick renewables source: API sim for offline, otherwise local
        renew_df = renew_df_api or renew_df_local

        # Transformations
        enriched = clean_and_join(api_df, aq_df, renew_df, include_fahrenheit=args.include_fahrenheit)
        if args.include_fahrenheit:
            enriched = add_temp_fahrenheit(enriched)

        # KPIs
        kpis = compute_kpis(enriched)

        # Save enriched parquet
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        enriched["date"] = enriched["date"].astype(str)
        kpis["daily_city"]["date"] = kpis["daily_city"]["date"].astype(str)

        merged = enriched.merge(
            kpis["daily_city"][["city", "date", "avg_aqi", "co2_7d_ma", "co2_7d_delta"]],
            on=["city", "date"], how="left"
        )
        merged.to_parquet(args.output, index=False)

        print("\n=== Enriched sample ===")
        print(merged.head(10).to_string(index=False))

        # Save KPI CSVs
        kpi_dir = "data/kpis"
        os.makedirs(kpi_dir, exist_ok=True)
        kpis["daily_city"].to_csv(os.path.join(kpi_dir, "daily_city.csv"), index=False)
        kpis["aqi_categories"].to_csv(os.path.join(kpi_dir, "aqi_categories.csv"), index=False)
        kpis["alignment"].to_csv(os.path.join(kpi_dir, "alignment.csv"), index=False)

        log.info({
            "event": "run_succeeded",
            "rows_enriched": len(merged),
            "output": args.output,
            "kpi_files": list(os.listdir(kpi_dir))
        })

    except Exception as e:
        logging.getLogger().exception({"event": "run_failed", "error": str(e)})
        raise

if __name__ == "__main__":
    main()