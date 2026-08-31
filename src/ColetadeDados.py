import sys
from pathlib import Path

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry


# Configura o cliente Open-Meteo com cache e novas tentativas em caso de falha.
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
PARAMS = {
    "latitude": -23.5489,
    "longitude": -46.6388,
    "start_date": "2024-09-06",
    "end_date": "2026-09-06",
    "hourly": [
        "pm10",
        "pm2_5",
        "carbon_monoxide",
        "carbon_dioxide",
        "nitrogen_dioxide",
        "sulphur_dioxide",
        "ozone",
    ],
}
OUTPUT_CSV = Path("dados_saida") / "qualidade_do_ar_por_dia.csv"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    responses = openmeteo.weather_api(URL, params=PARAMS)
    response = responses[0]

    print(f"Coordenadas: {response.Latitude()} graus N, {response.Longitude()} graus E")
    print(f"Elevacao: {response.Elevation()} m")
    print(f"Diferenca para GMT+0: {response.UtcOffsetSeconds()} segundos")

    # A ordem das variaveis deve ser a mesma da lista em PARAMS["hourly"].
    hourly = response.Hourly()
    hourly_pm10 = hourly.Variables(0).ValuesAsNumpy()
    hourly_pm2_5 = hourly.Variables(1).ValuesAsNumpy()
    hourly_carbon_monoxide = hourly.Variables(2).ValuesAsNumpy()
    hourly_carbon_dioxide = hourly.Variables(3).ValuesAsNumpy()
    hourly_nitrogen_dioxide = hourly.Variables(4).ValuesAsNumpy()
    hourly_sulphur_dioxide = hourly.Variables(5).ValuesAsNumpy()
    hourly_ozone = hourly.Variables(6).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        ),
        "pm10": hourly_pm10,
        "pm2_5": hourly_pm2_5,
        "carbon_monoxide": hourly_carbon_monoxide,
        "carbon_dioxide": hourly_carbon_dioxide,
        "nitrogen_dioxide": hourly_nitrogen_dioxide,
        "sulphur_dioxide": hourly_sulphur_dioxide,
        "ozone": hourly_ozone,
    }

    hourly_dataframe = pd.DataFrame(data=hourly_data)
    # Consolida as 24 medicoes horarias em uma media para cada dia.
    daily_dataframe = (
        hourly_dataframe.set_index("date").resample("D").mean().reset_index()
    )
    daily_dataframe["date"] = daily_dataframe["date"].dt.strftime("%Y-%m-%d")

    OUTPUT_CSV.parent.mkdir(exist_ok=True)
    daily_dataframe.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("\nDados diarios:\n", daily_dataframe)
    print(f"\nCSV salvo em: {OUTPUT_CSV.resolve()}")


if __name__ == "__main__":
    main()
