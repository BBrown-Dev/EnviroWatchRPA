# EnviroWatchRPA - Environmental Data Pipeline

## 1. Objective
Automate a previously manual analyst workflow into a reliable, auditable, and observable Python pipeline that:
- **Acquires signals:** Retrieves environmental data from live APIs or offline synthetic generation.
- **Enriches context:** Integrates local datasets for city-level interpretation and KPIs.
- **Computes KPIs:** Applies transparent, reproducible logic for trend and category metrics.
- **Persists outputs:** Produces structured files for analytics, dashboards, and reporting.

---

## 2. Design principles
- **Reliability:** Idempotent runs, fault-tolerant logic, schema-driven transformations.
- **Traceability:** Explicit, documented joins, conversions, and aggregations.
- **Observability:** Structured JSON logs, KPI verification, and actionable error context.
- **Extensibility:** Minimal-friction adaptation to new data providers or schema changes.

---

## 3. Data sources and schema
### 3.1 Remote (online mode)
- **Weather + metadata API:** Station-level rows with:
  - `date`, `station_id`, `city`, `lat`, `lon`
  - `temp_c`, `temp_f`, `humidity`, `precip_mm`

### 3.2 Local
- **SQLite — air_quality**
  - Fields: `station_id`, `date`, `aqi`, `co2_ppm`
  - Key: `(station_id, date)`
- **CSV — renewable_share**
  - Fields: `city`, `renewable_share` (0–1 float)

### 3.3 Offline simulation
- **Synthetic generation:** Creates station/date climate series plus air quality when absent.
- **Dual-unit persistence:** Weather rows include both Celsius (`temp_c`) and Fahrenheit (`temp_f`) to avoid downstream ambiguity.

---

## 4. Transformations
- **Cleaning:** Type coercion, range validation, null handling, and deduplication.
- **Joining:**
  1. **Station/date join:** `(station_id, date)` between weather and air_quality.
  2. **City enrichment:** `(city)` to attach `renewable_share`.
- **Enrichment:** Ensures `temp_f` is present and consistent with `temp_c` for all modes.
- **Aggregation:** Rolling window metrics and categorical tallies at city/day grain.

---

## 5. KPIs
1. **Average AQI** by city/day.
2. **CO₂ 7‑day rolling average** (`co2_7d_ma`).
3. **CO₂ day‑over‑day delta** (`co2_7d_delta`).
4. **AQI category day counts** by city.
5. **Clean energy alignment:** City/day meets renewable and air quality criteria.

---

## 6. Outputs
| Output type          | Location                       | Notes                            |
|----------------------|--------------------------------|----------------------------------|
| Enriched dataset     | `data/final_enriched.parquet`  | Includes `temp_c` & `temp_f`     |
| Daily KPIs (CSV)     | `data/kpis/daily_city.csv`     | Includes CO₂ trends              |
| AQI categories (CSV) | `data/kpis/aqi_categories.csv` | Categorized AQI days             |
| Alignment (CSV)      | `data/kpis/alignment.csv`      | Renewable/AQI alignment flag     |
| Logs                 | `data/logs/app.log`            | JSON, rotated                    |

---

## 7. Execution and configuration
- **Environment:** `.env` for API base URLs, keys, and runtime settings.
- **CLI arguments:**
  - **Mode:** `--offline` or `--online`
  - **Window:** `--start-date`, `--end-date`
  - **Paths:** `--db-path`, `--output`
  - **Logging:** `--log-level` (`DEBUG|INFO|...`)
  - **Units:** `--include-fahrenheit` (no-op if `temp_f` is already persisted)

---

## 8. Testing strategy
- **Temperature logic:** Verifies accurate °C↔°F conversion and dual-unit consistency.
- **CO₂ trends:** Validates rolling averages and day-over-day deltas on controlled series.
- **Integration correctness:** Ensures key joins and city enrichment behave under missing/synthetic data.

---

## 9. Limitations and assumptions
- **Provider normalization:** External API schemas are mapped to an internal canonical form.
- **Renewable proxy:** `renewable_share` is a simplified proxy, not a complete energy mix model.
- **Temporal gaps:** Rolling windows assume daily cadence; limited gaps tolerated with `min_periods=1`.

---

## 10. Future enhancements
- **Config-driven mappings:** Pluggable adapters for multiple API providers.
- **Operational alerts:** Threshold-based notifications for KPI anomalies or ingest failures.
- **Dashboard sync:** Optional auto-refresh hooks for downstream BI dashboards.