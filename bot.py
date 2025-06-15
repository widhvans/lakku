import logging
import sys
from pyromod import Client
from config import Config
from pyrogram import enums

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

class Bot(Client):
    def __init__(self):
        super().__init__(
            "FinalStorageBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="handlers")
        )
        self.me = None

    async def start(self):
        await super().start()
        self.me = await self.get_me()
        logger.info(f"Bot @{self.me.username} logged in and started successfully.")

        # --- CRITICAL STARTUP CHECK ---
        # This will verify the connection to your Owner Database Channel.
        if Config.OWNER_DATABASE_CHANNEL == 0:
            logger.error("FATAL ERROR: OWNER_DATABASE_CHANNEL is not set in config.py. Please set it.")
            sys.exit()
        
        try:
            logger.info(f"Verifying access to Owner Database Channel: {Config.OWNER_DATABASE_CHANNEL}...")
            chat = await self.get_chat(Config.OWNER_DATABASE_CHANNEL)
            if not chat.type == enums.ChatType.CHANNEL:
                 logger.error(f"FATAL ERROR: The ID {Config.OWNER_DATABASE_CHANNEL} is not a channel. It might be a group or user ID.")
                 sys.exit()
            logger.info(f"✅ Successfully connected to Owner Database Channel: {chat.title}")
        except Exception as e:
            logger.error(f"❌ FATAL ERROR: Could not access OWNER_DATABASE_CHANNEL ({Config.OWNER_DATABASE_CHANNEL}).")
            logger.error("➡️ Please make sure the bot is an ADMIN in that channel and the ID in config.py is correct.")
            logger.error(f"   Error details: {e}")
            logger.info("Bot is shutting down to prevent further errors.")
            sys.exit()
        # --- END OF STARTUP CHECK ---

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    Bot().run()
