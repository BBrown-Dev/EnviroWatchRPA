# EnviroWatchRPA environmental data pipeline

## Objective
Replace a manual analyst workflow with a robust Python pipeline that retrieves environmental signals, merges them with local tabular data, computes KPIs, and stores enriched outputs for analytics and reporting.

## Approach
- Data ingestion from an external API (or simulated offline).
- Local data from SQLite (air quality and CO₂) and a file-based renewable share source.
- Transformations: cleaning, joins, aggregations, rolling trends.
- Storage to Parquet with accompanying CSV KPI exports.
- Observability via JSON logs, rotation, and graceful fallbacks.

## Data sourcing and generation
- Online mode fetches station-level weather/metadata (date, station_id, city, temp, humidity, precipitation).
- Offline mode synthesizes realistic station, date, and climate-like signals across multiple cities.
- Local SQLite contains `air_quality` with `aqi` and `co2_ppm`. If missing and offline, it’s generated.
- Renewable share is loaded from `data/renewable_share.csv` or simulated if absent.

## Transformations and KPIs
- Joins by `station_id` and `date`, then by `city` for renewable share.
- Cleaning: type coercion, missing value handling, duplicate removal.
- KPIs:
  - Average AQI by city/day.
  - 7-day rolling average of CO₂ and day-over-day delta by city.
  - AQI category days by city.
  - Clean energy alignment signal (renewable_share ≥ 0.5 and avg_aqi ≤ 100 ⇒ “Aligned”).

## Outputs
- Enriched dataset: `data/final_enriched.parquet`.
- KPI CSVs: `data/kpis/daily_city.csv`, `aqi_categories.csv`, `alignment.csv`.
- JSON logs with rotation in `data/logs/app.log`.

## Configuration and execution
- Environment via `.env` (API endpoint, keys, timeouts, retries).
- CLI args for offline mode, dates, DB path, output path, log level.

## Testing
- Unit test validates KPI correctness for rolling CO₂ deltas on a controlled dataset.

## Limitations and assumptions
- API schema mapped into a normalized shape; adapt parser for a specific provider.
- Renewable share is a simplified proxy for clean energy adoption.
- Rolling window assumes daily frequency without gaps (small gaps handled by rolling min_periods=1).