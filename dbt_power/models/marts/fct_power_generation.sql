{{ config(
    materialized='incremental',
    unique_key=['country', 'ts_utc', 'production_type'],
    incremental_strategy='merge'
) }}

select
    country,
    ts_utc,
    production_type,
    category,
    unit,
    renewable_share,
    value,
    loaded_at
from {{ ref('stg_public_power_enriched') }}

{% if is_incremental() %}
where ts_utc >= (select max(ts_utc) - interval '7 days' from {{ this }})
{% endif %}