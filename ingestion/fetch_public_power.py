import json
import os
import time

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.energy-charts.info/public_power"

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": 5432,
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}


def fetch_public_power(country, date_from, date_to):
    """Fetch generation data from the API. Returns parsed JSON and request URL."""
    params = {
        "country": country,
        "start": date_from,
        "end": date_to,
    }

    response = requests.get(API_URL, params=params, timeout=30)
    if response.status_code == 429:
        # The API rate-limits bursts. Backfill fans out over many days at
        # once, so this is expected under load rather than a hard failure.
        retry_after = int(response.headers.get("Retry-After", 30))
        print(f"Rate limited, sleeping {retry_after}s before failing the task")
        time.sleep(retry_after)
        response.raise_for_status()
    if response.status_code == 404:
        # The API returns 404 when no data exists for the requested window.
        # This is expected for countries that publish with a longer delay,
        # not a failure: the next run will pick the data up.
        return None, response.url

    response.raise_for_status()

    return response.json(), response.url


def save_to_raw(payload, source_url, country, date_from, date_to):
    """Store the raw API response in the landing table."""
    points_received = len(payload.get("unix_seconds", []))

    sql = """
        INSERT INTO raw.public_power
            (country, requested_from, requested_to,
             source_url, payload, points_received)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, (
                country,
                date_from,
                date_to,
                source_url,
                json.dumps(payload),
                points_received,
            ))
    finally:
        conn.close()


    return points_received

def count_recent_empty_loads(country, window_hours=12):
    """Count how many recent load attempts for a country produced no data.

    An empty result on its own is normal — some countries publish with a
    longer delay. A long run of them is not: it usually means the endpoint,
    the country code or the API contract has changed.
    """
    sql = """
        select count(*)
        from raw.public_power
        where country = %s
          and loaded_at >= now() - make_interval(hours => %s)
          and points_received = 0
    """

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, (country, window_hours))
            return cur.fetchone()[0]
    finally:
        conn.close()

def main():
    country = "de"
    date_from = "2026-08-15T00:00"
    date_to = "2026-08-15T01:00"

    print(f"Fetching {country} data from {date_from} to {date_to}")

    payload, url = fetch_public_power(country, date_from, date_to)
    points = save_to_raw(payload, url, country, date_from, date_to)

    print(f"Saved response with {points} points to raw.public_power")


if __name__ == "__main__":
    main()