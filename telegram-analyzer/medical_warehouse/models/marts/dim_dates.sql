-- dim_dates: a calendar dimension table.
-- One row per date, covering the full range of dates seen in the messages.
-- This is a common dbt pattern: generate a date spine using generate_series,
-- rather than hardcoding a date range.

with date_range as (

    -- Find the earliest and latest message dates so we know how big
    -- a calendar to generate. We pad a few days on each side just in case.
    select
        min(message_date)::date - interval '1 day'  as start_date,
        max(message_date)::date + interval '1 day'  as end_date
    from {{ ref('stg_telegram_messages') }}

),

date_spine as (

    -- generate_series produces one row per day between start and end.
    -- This is the "date spine" - every single calendar day in range,
    -- whether or not a message was actually posted that day.
    select
        generate_series(start_date, end_date, interval '1 day')::date as full_date
    from date_range

),

final as (

    select
        -- surrogate key: a date formatted as an integer, e.g. 2026-06-25 -> 20260625
        -- this is a very common convention for date keys in dimensional models
        to_char(full_date, 'YYYYMMDD')::int     as date_key,

        full_date,
        extract(dow from full_date)::int        as day_of_week,      -- 0=Sunday ... 6=Saturday
        to_char(full_date, 'Day')               as day_name,
        extract(week from full_date)::int       as week_of_year,
        extract(month from full_date)::int      as month,
        to_char(full_date, 'Month')             as month_name,
        extract(quarter from full_date)::int    as quarter,
        extract(year from full_date)::int       as year,
        (extract(dow from full_date) in (0, 6)) as is_weekend

    from date_spine

)

select * from final