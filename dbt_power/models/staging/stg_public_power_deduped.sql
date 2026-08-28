with ranked as (
    select
        *,
        row_number() over (
            partition by country, ts_utc, production_type
            order by (value is null), loaded_at desc
        ) as rn
    from {{ ref('stg_public_power') }}
)
select
    country,
    ts_utc,
    production_type,
    value,
    loaded_at
from ranked
where rn = 1