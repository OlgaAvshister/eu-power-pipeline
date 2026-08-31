import sys
from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

sys.path.insert(0, "/opt/airflow")

from ingestion.fetch_public_power import (
    fetch_public_power,
    save_to_raw,
)

COUNTRIES = ["de", "fr"]

# How far back the daily reload reaches. Two concerns drive this number:
# some countries publish more than a day late, and the source revises
# already-published values for several days after the fact.
BACKFILL_DAYS = 7


@dag(
    dag_id="public_power_backfill",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 8, 30, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=2,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=10),
    },
    tags=["ingestion", "energy", "backfill"],
)
def public_power_backfill():

    @task
    def reload_country_day(job: dict):
        country = job["country"]
        day_offset = job["day_offset"]

        day = pendulum.now("UTC").start_of("day").subtract(days=day_offset)

        date_from = day.strftime("%Y-%m-%dT%H:%M")
        date_to = day.add(days=1).strftime("%Y-%m-%dT%H:%M")

        print(f"Reloading {country} for {date_from} to {date_to}")

        payload, url = fetch_public_power(country, date_from, date_to)

        if payload is None:
            save_to_raw({}, url, country, date_from, date_to)
            print(f"No data available for {country} on {date_from}")
            return 0

        points = save_to_raw(payload, url, country, date_from, date_to)
        print(f"Reloaded {points} points for {country} on {date_from}")
        return points

    jobs = [
        {"country": country, "day_offset": offset}
        for country in COUNTRIES
        for offset in range(1, BACKFILL_DAYS + 1)
    ]

    reload_country_day.expand(job=jobs)


public_power_backfill()