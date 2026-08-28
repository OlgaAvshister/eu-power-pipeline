-- Generation mix by source over time, Germany.
-- Area chart: timestamp on X, production type as series.

select
    ts_utc,
    production_type,
    sum(value) as total_mw
from staging_marts.fct_power_generation
where category = 'generation'
  and country = 'de'
  and ts_utc >= '2026-08-28'
group by ts_utc, production_type
order by ts_utc