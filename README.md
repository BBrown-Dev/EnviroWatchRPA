# EnviroWatchRPA - Environmental Data Pipeline

This RPA project replaces a manual analyst workflow with a **robust, observable Python pipeline** that can run online (live API) or offline (synthetic but realistic).  
It emphasizes **reliability, traceability, and measurable business value**.

## Features
- **Online/Offline ingestion**
  - Online: API fetch of weather/metadata + air quality
  - Offline: Synthetic data generation (`air_quality` + `weather_by_station` with temp_c & temp_f)
- **Dual temperature units:** All weather data stored in °C (`temp_c`) and °F (`temp_f`)
- **Data integration:** Joins API, SQLite, and CSV renewable share datasets
- **KPI calculations:** Average AQI, CO₂ trends, AQI category counts, clean energy alignment
- **JSON logging:** Rotating logs with structured fields
- **CLI control:** Flexible runtime options for mode, dates, DB paths, outputs
- **Test coverage:** Validates KPI correctness and Fahrenheit conversion