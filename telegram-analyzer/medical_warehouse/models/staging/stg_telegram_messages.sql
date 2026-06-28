-- Staging model: cleans and standardizes raw Telegram messages.
-- Reads from raw.telegram_messages (via source()), casts types,
-- renames to consistent snake_case, filters invalid rows, and
-- adds a couple of calculated fields used later in the marts.

with source as (

    select *
    from {{ source('raw', 'telegram_messages') }}

),

renamed as (

    select
        -- identifiers
        channel                                    as channel_name,
        message_id,
        scraped_date,

        -- cast date properly - raw_data->>'date' comes back as text from JSONB
        (raw_data->>'date')::timestamp             as message_date,

        -- text content - Telethon's to_dict() calls this field "message"
        raw_data->>'message'                       as message_text,

        -- engagement metrics - cast from text to integer, defaulting nulls to 0
        coalesce((raw_data->>'views')::int, 0)     as view_count,
        coalesce((raw_data->>'forwards')::int, 0)  as forward_count,

        -- media: the raw "media" key is null if there's no attachment,
        -- or a nested object (e.g. {"_": "MessageMediaPhoto", ...}) if present
        raw_data->'media'                          as media_raw

    from source

),

cleaned as (

    select
        channel_name,
        message_id,
        scraped_date,
        message_date,
        message_text,
        view_count,
        forward_count,

        -- calculated field: message length (0 if text is null)
        coalesce(length(message_text), 0)          as message_length,

        -- calculated field: simple boolean flag for "does this message have media"
        (media_raw is not null)                    as has_image

    from renamed

    -- filter out invalid records: skip rows with no message_id or no date,
    -- since those would break joins/keys downstream
    where message_id is not null
      and message_date is not null

)

select * from cleaned