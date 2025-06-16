import logging
import sys
import os
import asyncio
from pyromod import Client
from aiohttp import web
from config import Config
from database.db import get_user, save_file_data
from utils.helpers import create_post
from handlers.new_post import get_batch_key

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
        with open("bot_username.txt", 'r') as f:
            bot_username = f.read().strip().replace("@", "")
    except FileNotFoundError:
        logger.error(f"FATAL: bot_username.txt not found!")
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
        self.web_app = None
        self.web_runner = None
        self.file_queue = asyncio.Queue()
        self.file_batch = {}
        self.batch_locks = {}

    async def file_processor_worker(self):
        logger.info("File processor worker started.")
        while True:
            try:
                message_to_process, user_id = await self.file_queue.get()
                
                # Directly use the ID from config, assuming it's correct.
                # Error handling is now inside the new_file_handler.
                copied_message = await message_to_process.copy(chat_id=Config.OWNER_DATABASE_CHANNEL)
                
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
            except Exception as e:
                logger.exception("Error in file processor worker")
                try:
                    await self.send_message(Config.ADMIN_ID, f"⚠️ **A critical error occurred in the file processor worker.**\n\n`{e}`\n\nThis is likely a problem with the Owner Database Channel setup. Please check my logs and your bot's admin status.")
                except: pass
            finally:
                self.file_queue.task_done()

    async def process_batch_task(self, user_id, batch_key):
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
        
        try:
            with open("bot_username.txt", 'w') as f:
                f.write(f"@{self.me.username}")
            logger.info(f"Updated bot username to @{self.me.username} in bot_username.txt")
        except Exception as e:
            logger.error(f"Could not write to bot_username.txt. Error: {e}")
        
        asyncio.create_task(self.file_processor_worker())
        await self.start_web_server()
        logger.info(f"Bot @{self.me.username} and all services started successfully.")

    async def stop(self, *args):
        logger.info("Stopping bot and web server...")
        if self.web_runner:
            await self.web_runner.cleanup()
        await super().stop()
        logger.info("Bot stopped.")

if __name__ == "__main__":
    Bot().run()
