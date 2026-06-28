import os
import json
import glob
import logging
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")

DATA_LAKE_BASE_DIR = os.path.join("data", "raw", "telegram_messages")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def get_connection():
    """Open a connection to Postgres using credentials from .env"""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def create_raw_table(conn):
    """
    Create raw.telegram_messages if it doesn't already exist.

    Design choice: we store the FULL original message as JSONB in
    'raw_data' (preserving the original API structure, as the task
    requires), while also pulling out a few fields as real columns
    (channel, message_id, scraped_date) so we can index/query/dedupe
    without having to dig into the JSON every time.
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS raw.telegram_messages (
        id SERIAL PRIMARY KEY,
        channel TEXT NOT NULL,
        message_id BIGINT NOT NULL,
        scraped_date DATE NOT NULL,
        raw_data JSONB NOT NULL,
        loaded_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (channel, message_id)
    );
    """
    with conn.cursor() as cur:
        cur.execute(create_sql)
    conn.commit()
    logging.info("Confirmed raw.telegram_messages table exists.")


def find_json_files():
    """
    Find every JSON file across all date-partitions, e.g.:
    data/raw/telegram_messages/2026-06-25/CheMed123.json
    data/raw/telegram_messages/2026-06-28/tikvahpharma.json
    Returns a list of (file_path, channel_name, scraped_date) tuples.
    """
    pattern = os.path.join(DATA_LAKE_BASE_DIR, "*", "*.json")
    files = glob.glob(pattern)

    results = []
    for file_path in files:
        # file_path looks like: data/raw/telegram_messages/2026-06-28/tikvahpharma.json
        parts = file_path.split(os.sep)
        scraped_date = parts[-2]                      # "2026-06-28"
        channel_name = parts[-1].replace(".json", "")  # "tikvahpharma"
        results.append((file_path, channel_name, scraped_date))

    return results


def load_file_into_postgres(conn, file_path, channel_name, scraped_date):
    """Read one JSON file and insert every message as a row."""
    with open(file_path, "r", encoding="utf-8") as f:
        messages = json.load(f)

    insert_sql = """
        INSERT INTO raw.telegram_messages (channel, message_id, scraped_date, raw_data)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (channel, message_id) DO NOTHING;
    """

    inserted_count = 0
    with conn.cursor() as cur:
        for message in messages:
            message_id = message.get("id")
            if message_id is None:
                continue  # skip anything malformed without an id

            cur.execute(
                insert_sql,
                (channel_name, message_id, scraped_date, Json(message)),
            )
            inserted_count += cur.rowcount  # 0 if skipped due to conflict, 1 if inserted

    conn.commit()
    logging.info(
        f"{channel_name} ({scraped_date}): {inserted_count} new rows inserted "
        f"(out of {len(messages)} messages in file)"
    )


def main():
    conn = get_connection()
    try:
        create_raw_table(conn)

        files = find_json_files()
        logging.info(f"Found {len(files)} JSON file(s) to load.")

        for file_path, channel_name, scraped_date in files:
            try:
                load_file_into_postgres(conn, file_path, channel_name, scraped_date)
            except Exception as e:
                logging.error(f"Failed to load {file_path}: {e}")
                conn.rollback()  # undo any partial work from this failed file

    finally:
        conn.close()
        logging.info("Postgres connection closed.")


if __name__ == "__main__":
    main()