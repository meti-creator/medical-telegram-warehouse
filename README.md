# Medical Telegram Warehouse

A data pipeline that scrapes public Telegram channels related to Ethiopian
medical/pharmaceutical/cosmetics businesses, stores the raw data in a JSON
data lake, loads it into PostgreSQL, and transforms it into a clean star
schema using dbt.

## Pipeline overview

```
Telegram channels
      │  (Telethon)
      ▼
data/raw/telegram_messages/{date}/{channel}.json   <- raw data lake
data/raw/images/{channel}/{message_id}.jpg          <- downloaded photos
      │  (load_to_postgres.py)
      ▼
raw.telegram_messages   (Postgres, JSONB column)
      │  (dbt)
      ▼
staging.stg_telegram_messages   <- cleaned, typed, calculated fields
      │
      ▼
marts.dim_channels   marts.dim_dates   marts.fct_messages   <- star schema
```

## Channels scraped

- CheMed123
- lobelia4cosmetics
- tikvahpharma

## Setup

1. Create a `.env` file in `telegram-analyzer/` with:
   ```
   API_ID=...
   API_HASH=...
   PG_HOST=localhost
   PG_PORT=5432
   PG_DATABASE=medical_warehouse
   PG_USER=postgres
   PG_PASSWORD=...
   ```
2. Install dependencies: `pip install -r requirements.txt`
3. Run the scraper: `python telegram-analyzer/scrape_messages.py`
4. Load raw data into Postgres: `python telegram-analyzer/load_to_postgres.py`
5. Run the dbt project:
   ```
   cd telegram-analyzer/medical_warehouse
   dbt run
   dbt test
   dbt docs generate
   ```

## Star schema design decisions

This project models messages using a standard **star schema**: one fact
table (`fct_messages`) surrounded by descriptive dimension tables
(`dim_channels`, `dim_dates`). This shape was chosen over a single flat
table for a few reasons:

- **Avoiding repeated data.** Channel attributes (type, first/last post
  date, total posts, average views) only need to be computed and stored
  once per channel, not recalculated or duplicated on every message row.
- **Query simplicity for analysis.** Questions like "average views per
  channel type" or "posting activity by day of week" become simple joins
  and group-bys against small dimension tables, rather than complex
  subqueries against the full message history.
- **Surrogate keys.** Both dimensions use generated surrogate keys
  (`channel_key`, `date_key`) rather than natural keys (channel username,
  calendar date) as the actual join keys. This is standard dimensional
  modeling practice — it decouples the warehouse's internal structure from
  the source system's identifiers, so if a channel's username ever changed,
  the warehouse key would remain stable.
- **`dim_dates` as a generated calendar spine.** Rather than only including
  dates that have messages, the date dimension is generated as a continuous
  calendar (via `generate_series`) covering the full range of message
  activity. This makes time-based analysis (e.g. "which days had zero
  posts") possible, which wouldn't work if the date dimension only included
  dates that already had messages.
- **`channel_type` as manually classified business logic.** Telegram's API
  doesn't expose a category for a channel's content, so `channel_type`
  (Pharmaceutical / Cosmetics / Medical) is manually assigned per channel
  based on known business context. This is a deliberate modeling decision:
  encoding business knowledge that doesn't exist in the raw source data is
  a normal and expected part of dimensional modeling.

## Known issues

- `dbt docs serve`'s rendered HTML has a cosmetic rendering bug with this
  dbt-core version (icon template tags appear unrendered, causing harmless
  404s in the console). `dbt docs generate` itself completes successfully
  and produces valid documentation artifacts in `target/`.