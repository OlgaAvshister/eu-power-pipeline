CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS raw.public_power (
    id              BIGSERIAL PRIMARY KEY,
    country         TEXT        NOT NULL,
    requested_from  TIMESTAMPTZ NOT NULL,
    requested_to    TIMESTAMPTZ NOT NULL,
    source_url      TEXT        NOT NULL,
    payload         JSONB       NOT NULL,
    points_received INTEGER     NOT NULL,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_public_power_country_loaded
    ON raw.public_power (country, loaded_at DESC);