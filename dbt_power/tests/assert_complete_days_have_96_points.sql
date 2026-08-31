-- Every settled day must contain 96 points per production type
-- (24 hours at 15-minute resolution).
-- The source truncates responses silently, so gaps would otherwise
-- go unnoticed: the data looks fine, it is just incomplete.
--
-- Excluded from the check:
--   - the last two days, which the source may still be catching up on.
--     Publication delay varies by country and has been observed to exceed
--     24 hours for France, so a stricter cutoff would fail on healthy data.
--   - days with very few points, which were never meant to be loaded in
--     full (manual exploration requests during source discovery)
--   - days older than the backfill horizon: the oldest day in the window
--     loads only partially, and days beyond it are never reloaded at all
--
-- A failure here means data has not arrived even after two days, which
-- points at a real gap rather than normal publication lag.

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
where day_utc < date_trunc('day', current_timestamp) - interval '2 days'
  and day_utc > date_trunc('day', current_timestamp) - interval '7 days'
  and points > 20
  and points <> 96