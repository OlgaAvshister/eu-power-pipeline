{{ config(
    materialized='incremental',
    unique_key=['country', 'ts_utc', 'production_type'],
    incremental_strategy='merge'
) }}

select
    country,
        ts_utc,
    ts_utc at time zone (
        case country
            when 'de' then 'Europe/Berlin'
            when 'fr' then 'Europe/Paris'
        end
    ) as ts_local,
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