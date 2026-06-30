import os
import csv
import psycopg2
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("PG_HOST")
PG_PORT = os.getenv("PG_PORT")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")

CSV_FILE = "yolo_detections.csv"


def get_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def create_table(conn):
    """
    Create raw.yolo_detections if it doesn't exist.
    One row per detected object (matching the CSV structure from yolo_detect.py).
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS raw.yolo_detections (
        id SERIAL PRIMARY KEY,
        channel TEXT NOT NULL,
        message_id BIGINT NOT NULL,
        detected_class TEXT,
        confidence_score NUMERIC,
        loaded_at TIMESTAMP DEFAULT NOW()
    );
    """
    with conn.cursor() as cur:
        cur.execute(create_sql)
    conn.commit()
    print("Confirmed raw.yolo_detections table exists.")


def load_csv(conn):
    """Read the CSV and insert every row into Postgres."""
    insert_sql = """
        INSERT INTO raw.yolo_detections (channel, message_id, detected_class, confidence_score)
        VALUES (%s, %s, %s, %s);
    """

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with conn.cursor() as cur:
        for row in rows:
            # confidence_score and detected_class may be blank strings
            # (from images where nothing confident was detected) - convert
            # those to None so Postgres stores a real NULL, not an empty string.
            confidence = row["confidence_score"] if row["confidence_score"] else None
            detected_class = row["detected_class"] if row["detected_class"] else None

            cur.execute(
                insert_sql,
                (row["channel"], row["message_id"], detected_class, confidence),
            )

    conn.commit()
    print(f"Inserted {len(rows)} rows from {CSV_FILE} into raw.yolo_detections.")


def main():
    conn = get_connection()
    try:
        create_table(conn)

        # Start fresh each run, so re-running this script after re-running
        # yolo_detect.py doesn't duplicate old results.
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE raw.yolo_detections;")
        conn.commit()

        load_csv(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()