import asyncio
from telethon import TelegramClient

# Replace these with your actual credentials from my.telegram.org
API_ID = 1234567  # Must be an integer
API_HASH = 'your_api_hash_string'
SESSION_NAME = 'my_telegram_session'

async def main():
    # Initialize the client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    # Start the client (this handles authentication)
    await client.start()
    print("Client successfully authorized!")
    
    # Get information about yourself
    me = await client.get_me()
    print(f"Logged in as: {me.username} (ID: {me.id})")
    
    # Always disconnect when done
    await client.disconnect()

# Run the async main function
if __name__ == '__main__':
    asyncio.run(main())
    