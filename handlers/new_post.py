import asyncio
import re
import logging
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from config import Config
from database.db import get_user, save_file_data, find_owner_by_db_channel
from utils.helpers import create_post

logger = logging.getLogger(__name__)
file_batch = {}
batch_locks = {}

def get_batch_key(filename: str):
    name = re.sub(r'\.\w+$', '', filename)
    name = re.sub(r'[\._]', ' ', name)
    delimiters = [
        r'S\d{1,2}', r'Season\s?\d{1,2}', r'Part\s?\d{1,2}', r'E\d{1,3}', r'EP\d{1,3}',
        r'\b(19|20)\d{2}\b', r'\b(4k|2160p|1080p|720p|480p)\b', r'\[.*?\]'
    ]
    match = re.search('|'.join(delimiters), name, re.I)
    base_name = name[:match.start()].strip() if match else name.strip()
    return re.sub(r'\s+', ' ', base_name).lower()

async def process_batch(client, user_id, batch_key):
    try:
        # Near-instant posting with a very small buffer to catch simultaneous files
        await asyncio.sleep(2)
        
        if user_id not in batch_locks or batch_key not in batch_locks[user_id]: return
        async with batch_locks[user_id][batch_key]:
            messages = file_batch[user_id].pop(batch_key, [])
            if not messages: return
            
            user = await get_user(user_id)
            post_channels = user.get('post_channels', [])
            if not post_channels: return

            poster, caption, footer_keyboard = await create_post(client, user_id, messages)
            
            if caption:
                for channel_id in post_channels:
                    try:
                        if poster:
                            await client.send_photo(channel_id, photo=poster, caption=caption, reply_markup=footer_keyboard)
                        else:
                            await client.send_message(channel_id, caption, reply_markup=footer_keyboard, disable_web_page_preview=True)
                    except Exception as e:
                        logger.error(f"Error posting to channel `{channel_id}`: {e}")
                        await client.send_message(user_id, f"Error posting to `{channel_id}`: {e}")
    
    except Exception:
        logger.exception(f"An error occurred in process_batch for user {user_id}")
    finally:
        # Cleanup
        if user_id in batch_locks and batch_key in batch_locks.get(user_id, {}):
            del batch_locks[user_id][batch_key]
        if user_id in file_batch and not file_batch.get(user_id, {}):
            del file_batch[user_id]
        if user_id in batch_locks and not batch_locks.get(user_id, {}):
            del batch_locks[user_id]


@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio), group=2)
async def new_file_handler(client, message):
    try:
        user_id = await find_owner_by_db_channel(message.chat.id)
        if not user_id: return

        media = getattr(message, message.media.value, None)
        if not media or not getattr(media, 'file_name', None): return
        
        owner_db_channel_id = await get_owner_db_channel()
        if not owner_db_channel_id:
            logger.warning(f"Owner Database Channel is not set. Cannot process file from user {user_id}.")
            if user_id == Config.ADMIN_ID:
                 await client.send_message(Config.ADMIN_ID, "⚠️ **Setup Incomplete:** Please set your Owner Database Channel in my settings so I can save files.")
            return

        # --- NEW "SMART COPY" METHOD ---
        # This is fast and removes the forward tag without slow downloads.
        copied_message = await message.copy(chat_id=owner_db_channel_id)
        
        await save_file_data(
            owner_id=user_id,
            original_message=message, # Used for metadata
            copied_message=copied_message # Used for the permanent link
        )
        # --- END OF NEW METHOD ---
        
        filename = media.file_name
        batch_key = get_batch_key(filename)

        if user_id not in batch_locks: batch_locks[user_id] = {}
        if batch_key not in batch_locks[user_id]:
            batch_locks[user_id][batch_key] = asyncio.Lock()
            
        async with batch_locks[user_id][batch_key]:
            if batch_key not in file_batch.setdefault(user_id, {}):
                file_batch[user_id][batch_key] = [copied_message]
                asyncio.create_task(process_batch(client, user_id, batch_key))
            else:
                file_batch[user_id][batch_key].append(copied_message)
                
    except Exception as e:
        logger.exception("Error in new_file_handler")
        # Notify the admin if the copy fails (usually due to a permissions issue)
        await client.send_message(Config.ADMIN_ID, f"⚠️ **CRITICAL ERROR in File Saving**\n\nI failed to copy a file to the Owner Database.\n\n**Reason:** `{e}`\n\nPlease ensure I am still an admin in that channel.")
