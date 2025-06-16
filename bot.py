import logging
import sys
import os
import asyncio
from pyrogram import enums
from pyromod import Client
from aiohttp import web
from config import Config

# --- Setup logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()])
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyromod").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- Web Server Handler ---
async def handle_redirect(request):
    """
    This function handles incoming web requests and redirects them to the bot.
    """
    file_unique_id = request.match_info.get('file_unique_id', None)
    if not file_unique_id:
        return web.Response(text="File ID missing.", status=400)
    
    try:
        with open(Config.BOT_USERNAME_FILE, 'r') as f:
            bot_username = f.read().strip().replace("@", "")
    except FileNotFoundError:
        logger.error(f"FATAL: Bot username file not found at {Config.BOT_USERNAME_FILE}")
        return web.Response(text="Bot configuration error.", status=500)
        
    # Construct the final Telegram deep link payload
    payload = f"get_{file_unique_id}"
    
    # Create the final URL and redirect the user
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
        self.web_app = None
        self.web_runner = None

    async def start_web_server(self):
        """Initializes and starts the aiohttp web server."""
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
        
        # Start the integrated web server
        await self.start_web_server()

    async def stop(self, *args):
        logger.info("Stopping bot and web server...")
        if self.web_runner:
            await self.web_runner.cleanup()
        await super().stop()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    Bot().run()
