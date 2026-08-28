-- The renewable share we compute from the production type dimension
-- must match the value reported by the source API.
-- A persistent gap means our classification has drifted from theirs.

with calculated as (

    select
        country,
        ts_utc,
        100.0 * sum(value * renewable_share) / nullif(sum(value), 0) as calc_share
    from {{ ref('fct_power_generation') }}
    where category = 'generation'
    group by country, ts_utc

),

reported as (

    select
        country,
        ts_utc,
        value as reported_share
    from {{ ref('fct_power_generation') }}
    where production_type = 'Renewable share of generation'
      and value is not null

)

select
    calculated.country,
    calculated.ts_utc,
    calculated.calc_share,
    reported.reported_share,
    abs(calculated.calc_share - reported.reported_share) as gap
from calculated
join reported using (country, ts_utc)
where abs(calculated.calc_share - reported.reported_share) > 0.5