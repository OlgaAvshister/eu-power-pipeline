with source as (

    select
        id as raw_id,
        country,
        payload,
        loaded_at
    from {{ source('raw', 'public_power') }}

),

unpivoted as (

    select
        source.raw_id,
        source.country,
        to_timestamp((ts.value::text)::bigint) as ts_utc,
        pt.value ->> 'name' as production_type,
        case
            when jsonb_typeof(val.value) = 'null' then null
            else (val.value::text)::numeric
        end as value,
        source.loaded_at
    from source,
         jsonb_array_elements(source.payload -> 'unix_seconds')
             with ordinality as ts(value, ordinality),
         jsonb_array_elements(source.payload -> 'production_types')
             as pt(value),
         jsonb_array_elements(pt.value -> 'data')
             with ordinality as val(value, ordinality)
    where ts.ordinality = val.ordinality

)

select * from unpivoted