-- How the source revises already-published values.
--
-- Built on the snapshot, which keeps every version the API has returned.
-- Answers questions the fact table cannot: how often values are restated,
-- how large the corrections are, and how long after publication they arrive.

with versions as (

    select
        country,
        ts_utc,
        production_type,
        value,
        dbt_valid_from,
        dbt_valid_to,
        row_number() over (
            partition by country, ts_utc, production_type
            order by dbt_valid_from
        ) as version_number
    from {{ ref('snap_power_generation') }}

),

revised as (

    select
        current_version.country,
        current_version.ts_utc,
        current_version.production_type,
        previous_version.value as previous_value,
        current_version.value as revised_value,
        current_version.value - previous_version.value as delta,
        current_version.version_number,
        current_version.dbt_valid_from as revised_at,
        extract(
            epoch from (current_version.dbt_valid_from - current_version.ts_utc)
        ) / 3600 as hours_after_measurement
    from versions as current_version
    join versions as previous_version
        on current_version.country = previous_version.country
       and current_version.ts_utc = previous_version.ts_utc
       and current_version.production_type = previous_version.production_type
       and current_version.version_number = previous_version.version_number + 1

)

select * from revised