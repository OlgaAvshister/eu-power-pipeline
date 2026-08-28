from datetime import datetime, timedelta

import pendulum
from airflow.sdk import dag, task

import sys
sys.path.insert(0, "/opt/airflow")

from ingestion.fetch_public_power import fetch_public_power, save_to_raw

COUNTRIES = ["de", "fr"]
LOOKBACK_HOURS = 6

@dag(
    dag_id="public_power_ingestion",
    schedule="@hourly",
    start_date=pendulum.datetime(2026, 8, 25, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["ingestion", "energy"],
)
def public_power_ingestion():

    @task
    def load_country(country: str, **context):
        logical_date = context["logical_date"]

        window_end = logical_date + timedelta(hours=1)
        window_start = window_end - timedelta(hours=LOOKBACK_HOURS)

        date_from = window_start.strftime("%Y-%m-%dT%H:%M")
        date_to = window_end.strftime("%Y-%m-%dT%H:%M")

        print(f"Fetching {country} from {date_from} to {date_to}")

        payload, url = fetch_public_power(country, date_from, date_to)
        points = save_to_raw(payload, url, country, date_from, date_to)

        print(f"Saved {points} points for {country}")
        return points

    load_country.expand(country=COUNTRIES)


public_power_ingestion()