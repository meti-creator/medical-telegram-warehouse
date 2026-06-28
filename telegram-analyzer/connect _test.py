import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient

# Load API_ID and API_HASH from the .env file
load_dotenv()
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")

# The 3 channels we're working with for this project
CHANNELS = [
    "CheMed123",
    "lobelia4cosmetics",
    "tikvahpharma",
]

# "session_name" creates a local file (session_name.session) that stores
# your login so you don't have to re-enter the code every time you run this.
with TelegramClient("session_name", api_id, api_hash) as client:
    print("Connected! Checking access to each channel...\n")

    for channel_username in CHANNELS:
        try:
            entity = client.get_entity(channel_username)
            print(f"✅ {channel_username} -> {entity.title} (id: {entity.id})")
        except Exception as e:
            print(f"❌ {channel_username} -> could not access: {e}")
            