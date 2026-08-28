with facts as (

    select * from {{ ref('stg_public_power_deduped') }}

),

types as (

    select * from {{ ref('production_types') }}

)

select
    facts.country,
    facts.ts_utc,
    facts.production_type,
    types.category,
    types.unit,
    types.is_renewable,
    facts.value,
    facts.loaded_at
from facts
left join types
    on facts.production_type = types.production_type