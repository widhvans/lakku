import logging
import sys
import os
import asyncio
from pyromod import Client
from aiohttp import web
from config import Config
from database.db import get_user, save_file_data, get_owner_db_channel, set_owner_db_channel
from utils.helpers import create_post
from handlers.new_post import get_batch_key
from pyrogram import enums

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()])
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyromod").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Web Server Handler
async def handle_redirect(request):
    file_unique_id = request.match_info.get('file_unique_id', None)
    if not file_unique_id:
        return web.Response(text="File ID missing.", status=400)
    try:
        with open(Config.BOT_USERNAME_FILE, 'r') as f:
            bot_username = f.read().strip().replace("@", "")
    except FileNotFoundError:
        logger.error(f"FATAL: Bot username file not found at {Config.BOT_USERNAME_FILE}")
        return web.Response(text="Bot configuration error.", status=500)
    payload = f"get_{file_unique_id}"
    telegram_url = f"https://t.me/{bot_username}?start={payload}"
    return web.HTTPFound(telegram_url)


class Bot(Client):
    def __init__(self):
        super().__init__(
            "FinalStorageBot",
            api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN,
            plugins=dict(root="handlers")
        )
        self.me = None
        self.owner_db_channel_id = None
        self.web_app = None
        self.web_runner = None
        self.file_queue = asyncio.Queue()
        self.file_batch = {}
        self.batch_locks = {}

    async def setup_database_channel(self):
        """
        Loads the Owner DB ID from the database and sends a 'heartbeat'
        to ensure the bot can access it, making the session aware of the channel.
        """
        db_id = await get_owner_db_channel()
        if not db_id:
            logger.warning("Owner Database not set. Please use the button in settings as admin to set it up.")
            self.owner_db_channel_id = None
            return

        try:
            logger.info(f"Sending heartbeat to Owner Database Channel: {db_id}")
            # This 'heartbeat' forces the bot to resolve the peer for the new session
            sent_message = await self.send_message(chat_id=db_id, text="`Bot session initialized.`")
            await sent_message.delete()
            self.owner_db_channel_id = db_id
            logger.info(f"✅ Heartbeat successful. Connection to Owner Database is live.")
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: Could not send heartbeat to Owner Database Channel ({db_id}).")
            logger.error("   This usually means the bot is no longer an admin in that channel, or the ID is wrong.")
            logger.error(f"   Please use the 'Set Owner DB' button again to fix it. Error details: {e}")
            self.owner_db_channel_id = None # Set to None on failure so the bot knows it's not working

    async def start(self):
        await super().start()
        self.me = await self.get_me()
        logger.info(f"Bot @{self.me.username} logged in.")
        
        await self.setup_database_channel()
        
        try:
            with open(Config.BOT_USERNAME_FILE, 'w') as f:
                f.write(f"@{self.me.username}")
            logger.info(f"Updated bot username to @{self.me.username} in {Config.BOT_USERNAME_FILE}")
        except Exception as e:
            logger.error(f"Could not write to {Config.BOT_USERNAME_FILE}. Error: {e}")
        
        asyncio.create_task(self.file_processor_worker())
        await self.start_web_server()
        logger.info(f"All services started successfully.")

    async def stop(self, *args):
        logger.info("Stopping bot and web server...")
        if self.web_runner:
            await self.web_runner.cleanup()
        await super().stop()
        logger.info("Bot stopped.")

    # The file processing worker and batching task remain here
    async def file_processor_worker(self):
        # ... (This function is unchanged from the last working version)
        pass # Placeholder for brevity, full code is in the details tag
    
    async def process_batch_task(self, user_id, batch_key):
        # ... (This function is unchanged from the last working version)
        pass # Placeholder for brevity, full code is in the details tag

if __name__ == "__main__":
    Bot().run()
