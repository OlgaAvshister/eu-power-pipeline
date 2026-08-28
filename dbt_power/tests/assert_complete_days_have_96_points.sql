-- Every completed day must contain 96 points per production type
-- (24 hours at 15-minute resolution).
-- The source truncates responses silently, so gaps would otherwise
-- go unnoticed: the data looks fine, it is just incomplete.
--
-- Excluded from the check:
--   - the current day, which is always partial by design
--   - days with very few points, which were never meant to be
--     loaded in full (manual exploration requests)

with daily_counts as (

    select
        country,
        date_trunc('day', ts_utc) as day_utc,
        production_type,
        count(*) as points
    from {{ ref('fct_power_generation') }}
    group by country, date_trunc('day', ts_utc), production_type

)

select
    country,
    day_utc,
    production_type,
    points
from daily_counts
where day_utc < date_trunc('day', current_timestamp)
  and points > 20
  and points <> 96