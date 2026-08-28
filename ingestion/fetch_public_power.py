import json
import os

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