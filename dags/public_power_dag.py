import sys
from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

sys.path.insert(0, "/opt/airflow")

from ingestion.fetch_public_power import (
    count_recent_empty_loads,
    fetch_public_power,
    save_to_raw,
)

COUNTRIES = ["de", "fr"]
# Covers the typical publication delay for fast-publishing countries.
# Slower countries and retroactive revisions are handled by the daily
# backfill DAG, not by widening this window.
LOOKBACK_HOURS = 6
MAX_CONSECUTIVE_EMPTY = 6
EMPTY_WINDOW_HOURS = 12

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
        # Scheduled runs carry a logical_date that defines the interval being
        # loaded. Manual runs do not, so fall back to the current hour — the
        # lookback window makes the exact boundary non-critical.
        logical_date = context.get("logical_date")
        if logical_date is None:
            logical_date = pendulum.now("UTC").start_of("hour")

        window_end = logical_date + timedelta(hours=1)
        window_start = window_end - timedelta(hours=LOOKBACK_HOURS)

        date_from = window_start.strftime("%Y-%m-%dT%H:%M")
        date_to = window_end.strftime("%Y-%m-%dT%H:%M")

        print(f"Fetching {country} from {date_from} to {date_to}")

        payload, url = fetch_public_power(country, date_from, date_to)

        if payload is None:
            save_to_raw({}, url, country, date_from, date_to)
            recent_empty = count_recent_empty_loads(country)
            print(
                f"No data published yet for {country} in this window "
                f"({recent_empty} empty results in the last {EMPTY_WINDOW_HOURS}h)"
            )
            if recent_empty >= MAX_CONSECUTIVE_EMPTY:
                raise RuntimeError(
                    f"No data for {country} in {recent_empty} consecutive attempts "
                    f"over the last {EMPTY_WINDOW_HOURS}h. "
                    f"This is unlikely to be publication delay — check the source."
                )
            return 0

        points = save_to_raw(payload, url, country, date_from, date_to)

        print(f"Saved {points} points for {country}")
        return points

    load_country.expand(country=COUNTRIES)


public_power_ingestion()