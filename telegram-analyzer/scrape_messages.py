import os
import csv
import json
import logging
from datetime import datetime, date
from dotenv import load_dotenv
from telethon.sync import TelegramClient

load_dotenv()
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

CHANNELS = [
    "CheMed123",
    "lobelia4cosmetics",
    "tikvahpharma",
]

MESSAGES_PER_CHANNEL = 100  # keep small while testing
OUTPUT_FILE = "messages.csv"
IMAGES_BASE_DIR = os.path.join("data", "raw", "images")
DATA_LAKE_BASE_DIR = os.path.join("data", "raw", "telegram_messages")
LOGS_DIR = "logs"
TODAY_STR = date.today().isoformat()  # e.g. "2026-06-25"


def setup_logging():
    """
    Configure logging so messages go to BOTH the console and a log file.
    One log file per day, e.g. logs/scrape_2026-06-25.log
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"scrape_{TODAY_STR}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),  # also print to console
        ],
    )


def get_media_type(message):
    """Return a simple label describing what kind of media (if any) is attached."""
    if message.photo:
        return "photo"
    elif message.document:
        # Documents cover videos, files, gifs, etc. - mime_type tells us more
        return f"document ({message.document.mime_type})"
    elif message.media:
        return type(message.media).__name__
    else:
        return "none"


def json_safe(obj):
    """
    json.dump() doesn't know how to handle datetime or bytes objects,
    which show up inside Telethon's message.to_dict() output.
    This function is passed as 'default' to json.dump so it knows
    how to convert those types into something JSON can store.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.hex()
    return str(obj)  # fallback: just stringify anything else unexpected


def save_to_data_lake(channel_username, raw_messages):
    """
    Save the raw (untouched) message data for one channel as JSON,
    partitioned by today's date:
    data/raw/telegram_messages/{YYYY-MM-DD}/{channel_name}.json
    """
    day_dir = os.path.join(DATA_LAKE_BASE_DIR, TODAY_STR)
    os.makedirs(day_dir, exist_ok=True)

    file_path = os.path.join(day_dir, f"{channel_username}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(raw_messages, f, default=json_safe, ensure_ascii=False, indent=2)

    return file_path


def download_photo_if_present(client, message, channel_username):
    """
    If this message has a photo, download it to:
    data/raw/images/{channel_name}/{message_id}.jpg
    Skips the download if the file already exists locally.
    Returns the file path used (or "" if no photo).
    """
    if not message.photo:
        return ""

    channel_dir = os.path.join(IMAGES_BASE_DIR, channel_username)
    os.makedirs(channel_dir, exist_ok=True)  # create folders if they don't exist yet

    file_path = os.path.join(channel_dir, f"{message.id}.jpg")

    if os.path.exists(file_path):
        # Already downloaded in a previous run - don't re-fetch
        return file_path

    client.download_media(message, file=file_path)
    return file_path


def main():
    setup_logging()
    rows = []

    with TelegramClient("session_name", api_id, api_hash) as client:
        for channel_username in CHANNELS:
            logging.info(f"Starting scrape for channel: {channel_username}")
            raw_messages = []  # untouched dicts, for the data lake

            try:
                entity = client.get_entity(channel_username)

                count = 0
                for message in client.iter_messages(entity, limit=MESSAGES_PER_CHANNEL):
                    # Keep the raw, unmodified dict for the JSON data lake
                    raw_messages.append(message.to_dict())

                    # Build the cleaned row for the CSV
                    image_path = download_photo_if_present(client, message, channel_username)
                    rows.append({
                        "channel": channel_username,
                        "message_id": message.id,
                        "date": message.date,
                        "text": message.text or "",
                        "views": message.views if message.views is not None else "",
                        "forwards": message.forwards if message.forwards is not None else "",
                        "media_type": get_media_type(message),
                        "image_path": image_path,
                    })
                    count += 1

                json_path = save_to_data_lake(channel_username, raw_messages)
                logging.info(
                    f"Finished {channel_username}: {count} messages -> {json_path}"
                )

            except Exception as e:
                # Catches rate limiting (FloodWaitError), network issues, etc.
                # We log it and move on to the next channel instead of crashing.
                logging.error(f"Failed to scrape {channel_username}: {e}")

    # Write everything to a CSV file
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "channel", "message_id", "date", "text", "views", "forwards", "media_type", "image_path"
        ])
        writer.writeheader()
        writer.writerows(rows)

    logging.info(f"Done! Saved {len(rows)} messages total to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()