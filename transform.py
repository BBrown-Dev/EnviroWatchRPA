# Module to clean and join air quality, weather, and renewable energy data,
# compute KPIs, and prepare for analysis.

from typing import Any
import pandas as pd
import numpy as np


# Convert Celsius to Fahrenheit with rounding
def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return round((celsius * 9 / 5) + 32, 1)


# Add a Fahrenheit temperature column to the DataFrame if not missing
# Requires 'temp_c' column to exist
def add_temp_fahrenheit(df: pd.DataFrame) -> pd.DataFrame:
    if "temp_c" not in df.columns:
        raise KeyError("Column 'temp_c' not found in DataFrame")
    if "temp_f" not in df.columns:
        df["temp_f"] = df["temp_c"].apply(c_to_f)
    return df


# Clean and join air quality, weather, and renewable energy data
def clean_and_join(api_df: pd.DataFrame, aq_df: pd.DataFrame, renew_df: pd.DataFrame, include_fahrenheit: bool = True) -> pd.DataFrame:
    """
    Returns a DataFrame with enriched data ready for KPI computation
    """

    # Normalize keys and types
    api = api_df.copy()
    aq = aq_df.copy()
    renew = renew_df.copy()

    # Coerce dates
    for df in (api, aq):
        df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)

    # Basic NA handling
    api["city"] = api["city"].fillna("Unknown")
    aq["aqi"] = pd.to_numeric(aq["aqi"], errors="coerce")
    aq["co2_ppm"] = pd.to_numeric(aq["co2_ppm"], errors="coerce")

    # Join air quality + api weather by station_id and date
    df = pd.merge(aq, api, on=["station_id", "date"], how="left")

    # Fill missing city with 'Unknown' before next merge
    df["city"] = df["city"].fillna("Unknown")

    # Join renewable share by city
    df = pd.merge(df, renew, on="city", how="left")

    # Fill numeric missings
    for col in ["temp_c", "humidity", "precip_mm"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())

    # Handle missing renewable_share
    if "renewable_share" in df:
        df["renewable_share"] = pd.to_numeric(df["renewable_share"], errors="coerce").fillna(
            df["renewable_share"].median())

    # Add Fahrenheit alongside Celsius if requested
    if include_fahrenheit and "temp_c" in df:
        df = add_temp_fahrenheit(df)

    # Drop obvious duplicates
    df = df.drop_duplicates(subset=["station_id", "date"])
    return df


# Computes KPIs from the cleaned data
def compute_kpis(df: pd.DataFrame) -> dict[str, Any]:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])

    # Average AQI by city/day
    daily_city = (
        d.groupby(["city", "date"], as_index=False)
        .agg(avg_aqi=("aqi", "mean"), avg_co2_ppm=("co2_ppm", "mean"))
    )

    # 7-day rolling CO2 mean and delta by city
    daily_city = daily_city.sort_values(["city", "date"])
    daily_city["co2_7d_ma"] = (
        daily_city.groupby("city")["avg_co2_ppm"]
        .transform(lambda s: s.rolling(window=7, min_periods=1).mean())
    )
    daily_city["co2_7d_delta"] = (
        daily_city.groupby("city")["co2_7d_ma"].diff().fillna(0.0)
    )

    # AQI category counts by city over the period
    def aqi_bucket(x):
        if x <= 50: return "Good"
        if x <= 100: return "Moderate"
        if x <= 150: return "Unhealthy for SG"
        return "Unhealthy+"

    d["aqi_bucket"] = d["aqi"].apply(aqi_bucket)
    aqi_cats = (
        d.groupby(["city", "aqi_bucket"], as_index=False)
        .size()
        .rename(columns={"size": "days_in_bucket"})
    )

    # Renewable alignment: simple signal mapping
    # If renewable_share >= 0.5 and avg_aqi <= 100 => "Aligned", else "Needs Improvement"
    last_by_city = (
        daily_city.sort_values("date").groupby("city").tail(1)[["city", "avg_aqi"]]
    )
    renew = df[["city", "renewable_share"]].drop_duplicates("city")
    alignment = last_by_city.merge(renew, on="city", how="left")
    alignment["clean_energy_alignment"] = np.where(
        (alignment["renewable_share"] >= 0.5) & (alignment["avg_aqi"] <= 100),
        "Aligned",
        "Needs Improvement",
    )

    # Final KPI package (granular daily + categorical summary + alignment)
    return {
        "daily_city": daily_city,
        "aqi_categories": aqi_cats,
        "alignment": alignment
    }
