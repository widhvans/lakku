import logging
import sys
from pyromod import Client
from config import Config

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
        # Startup check removed as requested.

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    Bot().run()
