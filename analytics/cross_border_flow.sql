-- Cross-border electricity flow, Germany vs France.
-- Line chart: timestamp on X, country as series.
-- Positive values indicate imports, negative values indicate exports.

select
    ts_utc,
    country,
    value as flow_mw
from staging_marts.fct_power_generation
where production_type = 'Cross-border electricity trading'
  and ts_utc >= current_date - interval '2 days'
order by ts_utc