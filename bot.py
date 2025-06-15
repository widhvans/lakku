import logging
import sys
from pyromod import Client
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
        # This will store the ID of the owner's database channel after joining
        self.owner_db_channel_id = None

    async def start(self):
        await super().start()
        self.me = await self.get_me()
        logger.info(f"Bot @{self.me.username} logged in and started successfully.")

        # --- NEW "JOIN VIA INVITE LINK" METHOD ---
        if not Config.OWNER_DB_INVITE_LINK or Config.OWNER_DB_INVITE_LINK == "YOUR_INVITE_LINK_HERE":
            logger.error("FATAL ERROR: OWNER_DB_INVITE_LINK is not set in config.py. Please set it.")
            sys.exit()
        
        try:
            logger.info("Attempting to join Owner Database Channel via invite link...")
            chat = await self.join_chat(Config.OWNER_DB_INVITE_LINK)
            self.owner_db_channel_id = chat.id
            logger.info(f"✅ Successfully joined and connected to Owner Database Channel: {chat.title}")
        except UserAlreadyParticipant:
            # If the bot is already in the channel, we need to get the chat ID
            try:
                chat = await self.get_chat(Config.OWNER_DB_INVITE_LINK)
                self.owner_db_channel_id = chat.id
                logger.info(f"✅ Bot is already a member of the Owner Database Channel: {chat.title}")
            except Exception as e:
                 logger.error(f"FATAL ERROR: Could not get chat info from invite link, even though bot is a member. Error: {e}")
                 sys.exit()
        except Exception as e:
            logger.error(f"❌ FATAL ERROR: Could not join Owner Database Channel using the provided invite link.")
            logger.error(f"   Please make sure the invite link '{Config.OWNER_DB_INVITE_LINK}' is correct and has not expired.")
            logger.error(f"   Error details: {e}")
            sys.exit()
        # --- END OF NEW METHOD ---

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    Bot().run()
