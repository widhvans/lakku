import logging
import sys
from pyromod import Client
from config import Config
from pyrogram import enums

# --- Professional Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyromod").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class Bot(Client):
    def __init__(self):
        super().__init__(
            "FinalStorageBot",
            api_id=Config.API_ID, api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN, plugins=dict(root="handlers")
        )
        self.me = None

    async def start(self):
        await super().start()
        self.me = await self.get_me()
        
        # --- Critical Startup Check ---
        if Config.OWNER_DATABASE_CHANNEL == 0:
            logger.critical("OWNER_DATABASE_CHANNEL is not set in config.py! Bot is shutting down.")
            sys.exit()
        try:
            chat = await self.get_chat(Config.OWNER_DATABASE_CHANNEL)
            if chat.type != enums.ChatType.CHANNEL:
                logger.critical(f"The ID for OWNER_DATABASE_CHANNEL does not belong to a channel. Bot is shutting down.")
                sys.exit()
            logger.info(f"Successfully connected to Owner Database Channel: {chat.title}")
        except Exception as e:
            logger.critical(f"FATAL: Could not access OWNER_DATABASE_CHANNEL ({Config.OWNER_DATABASE_CHANNEL}).")
            logger.critical("Please ensure the bot is an admin in that channel and the ID is correct.")
            logger.critical(f"Error details: {e}")
            sys.exit()
            
        logger.info(f"{self.me.first_name} | @{self.me.username} started successfully.")

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    Bot().run()
