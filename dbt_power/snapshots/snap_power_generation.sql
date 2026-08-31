{% snapshot snap_power_generation %}

{{
    config(
        target_schema='snapshots',
        unique_key="country || '|' || ts_utc || '|' || production_type",
        strategy='check',
        check_cols=['value'],
        invalidate_hard_deletes=False
    )
}}

-- Tracks how the source revises already-published values over time.
--
-- The pipeline itself always keeps the latest version, so revisions would
-- otherwise be invisible. This snapshot keeps every version the source has
-- returned, which makes it possible to measure how large the revisions are
-- and how long after publication they keep arriving.
--
-- Only settled measurements are tracked: the current day is excluded so
-- that normal publication lag is not mistaken for a revision.

select
    country,
    ts_utc,
    production_type,
    value
from {{ ref('fct_power_generation') }}
where ts_utc < date_trunc('day', current_timestamp)

{% endsnapshot %}