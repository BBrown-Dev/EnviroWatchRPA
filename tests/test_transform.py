# Tests for the transform module

import numpy as np
import pandas as pd
from transform import clean_and_join, compute_kpis


# Test the clean_and_join function with a controlled dataset
def test_co2_7d_delta_trend_and_fahrenheit_conversion():
    # Controlled 7-day dataset for a single city/station
    dates = pd.date_range("2025-01-01", periods=7, freq="D").astype(str)

    api = pd.DataFrame({
        "station_id": ["S1"] * 7,
        "date": dates,
        "city": ["TestCity"] * 7,
        "lat": [0.0] * 7,
        "lon": [0.0] * 7,
        "temp_c": [10.0] * 7,        # constant Celsius for easy F check (10C -> 50F)
        "humidity": [50] * 7,
        "precip_mm": [0.0] * 7
    })

    aq = pd.DataFrame({
        "station_id": ["S1"] * 7,
        "date": dates,
        "aqi": [50, 60, 70, 80, 90, 100, 110],
        "co2_ppm": [400, 402, 404, 406, 408, 410, 412]
    })

    renew = pd.DataFrame([{"city": "TestCity", "renewable_share": 0.6}])

    # Enrichment adds temp_f inside clean_and_join
    enriched = clean_and_join(api, aq, renew)

    # Sanity: one row per day
    assert len(enriched) == 7

    # Fahrenheit column exists and matches the conversion
    assert "temp_f" in enriched.columns
    expected_f = enriched["temp_c"].astype(float) * 9.0 / 5.0 + 32.0
    assert np.allclose(enriched["temp_f"].astype(float).values, expected_f.values, atol=1e-6)

    # KPI checks
    kpis = compute_kpis(enriched)
    daily = kpis["daily_city"].sort_values("date").reset_index(drop=True)

    # Rolling 7-day mean on last day: mean(400,402,404,406,408,410,412) = 406.0
    assert abs(daily.loc[6, "co2_7d_ma"] - 406.0) < 1e-6

    # Delta from day 1 to day 2 should be non-negative for this increasing series
    assert daily.loc[1, "co2_7d_delta"] >= 0.0