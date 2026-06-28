-- dim_channels: one row per Telegram channel, with descriptive
-- attributes and some pre-aggregated stats (first/last post, totals, avg views).
-- This is a "rolled up" dimension - it summarizes the fact data per channel,
-- which makes simple channel-level reporting fast (no need to re-aggregate
-- the full fact table every time you want "average views per channel").

with messages as (

    select * from {{ ref('stg_telegram_messages') }}

),

channel_stats as (

    select
        channel_name,
        min(message_date)      as first_post_date,
        max(message_date)      as last_post_date,
        count(*)                as total_posts,
        avg(view_count)         as avg_views

    from messages
    group by channel_name

),

-- channel_type is business knowledge that doesn't exist in the raw data -
-- we have to hardcode it ourselves based on what we know about each channel.
-- A case statement here is a simple, explicit way to do that.
final as (

    select
        -- surrogate key: a stable integer ID per channel, generated with
        -- dbt_utils-style row_number() since we don't have a natural numeric ID
        row_number() over (order by channel_name)  as channel_key,

        channel_name,

        case channel_name
            when 'CheMed123'           then 'Pharmaceutical'
            when 'lobelia4cosmetics'   then 'Cosmetics'
            when 'tikvahpharma'        then 'Pharmaceutical'
            else 'Medical'
        end                                          as channel_type,

        first_post_date,
        last_post_date,
        total_posts,
        round(avg_views::numeric, 2)                 as avg_views

    from channel_stats

)

select * from final
