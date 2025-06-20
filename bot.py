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
            sent_message = await self.send_message(chat_id=db_id, text="`Bot session initialized.`")
            await sent_message.delete()
            self.owner_db_channel_id = db_id
            logger.info(f"✅ Heartbeat successful. Connection to Owner Database is live.")
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: Could not send heartbeat to Owner Database Channel ({db_id}).")
            logger.error("   This usually means the bot is no longer an admin in that channel, or the ID is wrong.")
            logger.error(f"   Please use the 'Set Owner DB' button again to fix it. Error details: {e}")
            self.owner_db_channel_id = None

    async def file_processor_worker(self):
        """The single worker that processes files from the queue one by one."""
        logger.info("File processor worker started.")
        while True:
            try:
                message_to_process, user_id = await self.file_queue.get()
                
                if not self.owner_db_channel_id:
                    # FIX: Use the correct variable name 'message_to_process'
                    media = message_to_process.document or message_to_process.video or message_to_process.audio
                    filename = getattr(media, 'file_name', 'Unknown Filename')
                    logger.error(f"Owner DB not configured. Cannot process file '{filename}'. Worker is sleeping.")
                    await asyncio.sleep(60)
                    # Put the item back in the queue to be retried later
                    await self.file_queue.put((message_to_process, user_id))
                    continue

                copied_message = await message_to_process.copy(chat_id=self.owner_db_channel_id)
                await save_file_data(owner_id=user_id, original_message=message_to_process, copied_message=copied_message)
                
                filename = getattr(copied_message, copied_message.media.value).file_name
                batch_key = get_batch_key(filename)

                if user_id not in self.batch_locks: self.batch_locks[user_id] = {}
                if batch_key not in self.batch_locks[user_id]:
                    self.batch_locks[user_id][batch_key] = asyncio.Lock()
                
                async with self.batch_locks[user_id][batch_key]:
                    if batch_key not in self.file_batch.setdefault(user_id, {}):
                        self.file_batch[user_id][batch_key] = [copied_message]
                        asyncio.create_task(self.process_batch_task(user_id, batch_key))
                    else:
                        self.file_batch[user_id][batch_key].append(copied_message)
                
                await asyncio.sleep(2)
            except Exception:
                logger.exception("Error in file processor worker")
            finally:
                self.file_queue.task_done()

    async def process_batch_task(self, user_id, batch_key):
        """The task that waits and posts a batch of files."""
        try:
            await asyncio.sleep(10)
            if user_id not in self.batch_locks or batch_key not in self.batch_locks.get(user_id, {}): return
            async with self.batch_locks[user_id][batch_key]:
                messages = self.file_batch[user_id].pop(batch_key, [])
                if not messages: return
                
                user = await get_user(user_id)
                if not user or not user.get('post_channels'): return

                poster, caption, footer_keyboard = await create_post(self, user_id, messages)
                if not caption: return

                for channel_id in user.get('post_channels', []):
                    try:
                        if poster:
                            await self.send_photo(channel_id, photo=poster, caption=caption, reply_markup=footer_keyboard)
                        else:
                            await self.send_message(channel_id, caption, reply_markup=footer_keyboard, disable_web_page_preview=True)
                    except Exception as e:
                        await self.send_message(user_id, f"Error posting to `{channel_id}`: {e}")
        except Exception:
            logger.exception(f"An error occurred in process_batch_task for user {user_id}")
        finally:
            if user_id in self.batch_locks and batch_key in self.batch_locks.get(user_id, {}): del self.batch_locks[user_id][batch_key]
            if user_id in self.file_batch and not self.file_batch.get(user_id, {}): del self.file_batch[user_id]
            if user_id in self.batch_locks and not self.batch_locks.get(user_id, {}): del self.batch_locks[user_id]

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

if __name__ == "__main__":
    Bot().run()
