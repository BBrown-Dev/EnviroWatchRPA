# EnviroWatchRPA - Environmental Data Pipeline

---

## Introduction
EnviroWatchRPA is a Python-based Robotic Process Automation (RPA) pipeline that automates the collection, integration, and analysis of weather and air-quality data. It runs in online mode (live APIs) or offline mode (deterministic synthetic data) and stores dual temperature units (Celsius and Fahrenheit) for clarity and flexibility. The pipeline outputs an enriched dataset, KPI reports, and structured logs, emphasizing reliability, traceability, and measurable business value.

---

## Features
- **Ingestion modes:** Online API fetch or offline synthetic generation (schema-matched, seeded, deterministic).
- **Dual temperature units:** Authoritative `temp_c` with derived `temp_f` for downstream compatibility.
- **Data integration:** Weather + air quality + renewable-share enrichment into a unified model.
- **KPI coverage:** Average AQI, AQI category counts, trend metrics, and clean-energy alignment.
- **Storage & idempotency:** SQLite with upserts keyed by `(station_id, date)` to prevent duplicates.
- **Observability:** Structured JSON logging with rotation and clear runtime parameters.
- **CLI control:** Mode, date range, station list, DB/output paths, Fahrenheit inclusion, and log level.
- **Reproducibility:** Offline generator fills complete station–date grids to avoid gaps and first-run errors.
---

## Setup
- **Prerequisites**
  - Python 3.9 or later
  - SQLite (auto-created if missing)
  - Internet access only required for online mode
- **Environment configuration (`.env` at project root)**

  ```dotenv
  WEATHER_API_KEY=your_weather_api_key
  AIR_QUALITY_API_KEY=your_air_quality_api_key
  DB_PATH=./data/enviro.db
  OUTPUT_PATH=./data/final_enriched.parquet
  LOG_LEVEL=INFO
  DEFAULT_STATIONS=ECWI001,MSP001
  RANDOM_SEED=42
  ```
---

## Installation
```bash
git clone https://github.com/BBrown-Dev/EnviroWatchRPA.git
cd EnviroWatchRPA

python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
mkdir -p data data/kpis data/logs
```
---

## Usage
Run with defaults (online mode, last 14 days):
```bash
python main.py
```

### Common flags

| Flag                      | Description                                     |
| ------------------------- | ----------------------------------------------- |
| `--offline`               | Use synthetic data (no API calls)               |
| `--start-date YYYY-MM-DD` | Start date for the data window                   |
| `--end-date YYYY-MM-DD`   | End date for the data window (inclusive)         |
| `--db-path PATH`          | SQLite database file path                        |
| `--output PATH`           | Final Parquet output path                        |
| `--stations CSV`          | Comma-separated station IDs                      |
| `--include-fahrenheit`    | Persist `temp_f` in outputs                      |
| `--log-level LEVEL`       | DEBUG, INFO, WARNING, ERROR                      |


Examples:
```bash
# Offline, fixed window, deterministic
python main.py --offline --start-date 2025-08-01 --end-date 2025-08-14 \
  --stations ECWI001,MSP001 --db-path ./data/enviro.db \
  --output ./data/final_enriched.parquet --log-level INFO

# Online with Fahrenheit column in outputs
python main.py --stations ECWI001,MSP001 --include-fahrenheit

# Quiet logs for CI
python main.py --offline --log-level WARNING
```
---

## Outputs
- **SQLite database:** `./data/enviro.db`
  - `stations` — Station metadata (id, name, latitude, longitude).
  - `weather_by_station` — Per-station daily weather (`date`, `temp_c`, `temp_f`, `precip_mm`, …).
  - `air_quality` — Daily air-quality metrics (`date`, `aqi`, `pm25`, `pm10`, `o3`, `category`).
  - `enriched_daily` — Joined station + weather + air quality + derived KPIs.
- **Parquet dataset:** `./data/final_enriched.parquet` (analytics-ready).
- **KPI CSVs:** `./data/kpis/daily_city.csv`, `./data/kpis/aqi_categories.csv`, `./data/kpis/alignment.csv`.
- **Logs:** Structured JSON with rotation at `./data/logs/app.log`.

Data quality guarantees:
- **Completeness:** Offline generator fills every station–date pair in range.
- **Units:** `temp_c` is authoritative; `temp_f = temp_c * 9/5 + 32` is derived consistently.
- **Idempotency:** Upserts by `(station_id, date)` ensure reruns do not duplicate data.
---

## Testing
```bash
# Run full test suite
pytest -q

# Coverage report (if configured)
pytest --maxfail=1 --disable-warnings --cov=src --cov-report=term-missing

# Deterministic smoke test (offline)
rm -f ./data/enviro.db ./data/final_enriched.parquet ./data/kpis/*.csv
RANDOM_SEED=42 python main.py --offline --start-date 2025-08-01 --end-date 2025-08-07 --stations ECWI001,MSP001
test -f ./data/enviro.db && echo "DB OK"
test -f ./data/final_enriched.parquet && echo "Parquet OK"
ls -1 ./data/kpis/*.csv

# Quick integrity checks via SQLite
sqlite3 ./data/enviro.db "
  SELECT SUM(CASE WHEN temp_c IS NULL THEN 1 ELSE 0 END) AS null_temp_c,
         SUM(CASE WHEN temp_f IS NULL THEN 1 ELSE 0 END) AS null_temp_f
  FROM weather_by_station;

  WITH RECURSIVE dates(date) AS (
    SELECT MIN(date) FROM weather_by_station
    UNION ALL
    SELECT date(date, '+1 day') FROM dates
    WHERE date < (SELECT MAX(date) FROM weather_by_station)
  )
  SELECT COUNT(*) AS missing_pairs
  FROM stations s
  CROSS JOIN dates d
  LEFT JOIN weather_by_station w
    ON w.station_id = s.id AND w.date = d.date
  WHERE w.station_id IS NULL;
"
```