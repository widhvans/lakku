import logging
import sys
import os
import asyncio
from pyromod import Client
from aiohttp import web
from config import Config
from pyrogram.errors import UserAlreadyParticipant

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyromod").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- Web Server Handler (Unchanged) ---
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

    async def start_web_server(self):
        self.web_app = web.Application()
        self.web_app.router.add_get('/get/{file_unique_id}', handle_redirect)
        self.web_runner = web.AppRunner(self.web_app)
        await self.web_runner.setup()
        site = web.TCPSite(self.web_runner, Config.VPS_IP, Config.VPS_PORT)
        await site.start()
        logger.info(f"Web redirector server started at http://{Config.VPS_IP}:{Config.VPS_PORT}")

    async def start(self):
        await super().start()
        self.me = await self.get_me()
        logger.info(f"Bot @{self.me.username} logged in successfully.")
        
        # --- NEW: Automatically update the username file ---
        try:
            with open(Config.BOT_USERNAME_FILE, 'w') as f:
                f.write(f"@{self.me.username}")
            logger.info(f"Successfully updated bot username to @{self.me.username} in {Config.BOT_USERNAME_FILE}")
        except Exception as e:
            logger.error(f"Could not write to {Config.BOT_USERNAME_FILE}. Please check file permissions. Error: {e}")
        
        # Join Owner DB Channel via Invite Link
        if not Config.OWNER_DB_INVITE_LINK or Config.OWNER_DB_INVITE_LINK == "YOUR_INVITE_LINK_HERE":
            logger.error("FATAL ERROR: OWNER_DB_INVITE_LINK is not set in config.py.")
            sys.exit()
        try:
            chat = await self.join_chat(Config.OWNER_DB_INVITE_LINK)
            self.owner_db_channel_id = chat.id
            logger.info(f"✅ Successfully joined Owner Database Channel: {chat.title}")
        except UserAlreadyParticipant:
            try:
                chat = await self.get_chat(Config.OWNER_DB_INVITE_LINK)
                self.owner_db_channel_id = chat.id
                logger.info(f"✅ Bot is already in Owner Database Channel: {chat.title}")
            except Exception as e:
                 logger.error(f"FATAL ERROR: Could not get chat info from invite link. Error: {e}")
                 sys.exit()
        except Exception as e:
            logger.error(f"❌ FATAL ERROR: Could not join Owner Database Channel using invite link.")
            logger.error(f"   Error details: {e}")
            sys.exit()
            
        await self.start_web_server()

    async def stop(self, *args):
        logger.info("Stopping bot and web server...")
        if self.web_runner:
            await self.web_runner.cleanup()
        await super().stop()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    Bot().run()
