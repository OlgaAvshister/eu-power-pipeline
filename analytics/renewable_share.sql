-- Renewable share of generation, Germany vs France.
-- Line chart: timestamp on X, country as series.
-- Weighted by renewable_share from the production type dimension,
-- which treats waste as 50% renewable to match the source methodology.

select
    ts_utc,
    country,
    round(100.0 * sum(value * renewable_share) / nullif(sum(value), 0), 1) as renewable_pct
from staging_marts.fct_power_generation
where category = 'generation'
  and ts_utc >= '2026-08-28'
group by ts_utc, country
order by ts_utc