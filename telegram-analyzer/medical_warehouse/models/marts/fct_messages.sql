-- fct_messages: the fact table. One row per message.
-- Joins to dim_channels and dim_dates to replace natural keys
-- (channel_name, message_date) with their surrogate keys (channel_key, date_key).
-- This join pattern is the core mechanic of a star schema - the fact table
-- is "thin" (mostly keys + measures), and all descriptive detail lives in the dims.

with messages as (

    select * from {{ ref('stg_telegram_messages') }}

),

channels as (

    select channel_key, channel_name from {{ ref('dim_channels') }}

),

dates as (

    select date_key, full_date from {{ ref('dim_dates') }}

),

final as (

    select
        messages.message_id,
        channels.channel_key,
        dates.date_key,
        messages.message_text,
        messages.message_length,
        messages.view_count,
        messages.forward_count,
        messages.has_image

    from messages
    left join channels
        on messages.channel_name = channels.channel_name
    left join dates
        on messages.message_date::date = dates.full_date

)

select * from final