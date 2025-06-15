import asyncio
import re
import logging
import os
import tempfile
import shutil
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from config import Config
from database.db import get_user, save_file_data, find_owner_by_db_channel, get_owner_db_channel
from utils.helpers import create_post

logger = logging.getLogger(__name__)
file_batch = {}
batch_locks = {}

def get_batch_key(filename: str):
    """
    Final, most precise algorithm for grouping files.
    It cleans the filename to find a true 'base name'.
    """
    from utils.helpers import clean_filename
    # We use the same powerful cleaning function that we use for posters.
    # This ensures "Movie (2023) 1080p" and "Movie (2023) 720p" get the same key.
    base_title, _ = clean_filename(filename)
    return base_title.lower()

async def process_batch(client, user_id, batch_key):
    try:
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
        if user_id in batch_locks and batch_key in batch_locks.get(user_id, {}): del batch_locks[user_id][batch_key]
        if user_id in file_batch and not file_batch.get(user_id, {}): del file_batch[user_id]
        if user_id in batch_locks and not batch_locks.get(user_id, {}): del batch_locks[user_id]


@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio), group=2)
async def new_file_handler(client, message):
    try:
        user_id = await find_owner_by_db_channel(message.chat.id)
        if not user_id: return

        media = getattr(message, message.media.value, None)
        if not media or not getattr(media, 'file_name', None): return
        
        owner_db_channel_id = await get_owner_db_channel()
        if not owner_db_channel_id:
            logger.warning(f"Owner Database Channel is not set.")
            return

        copied_message = await message.copy(chat_id=owner_db_channel_id)
        
        await save_file_data(
            owner_id=user_id,
            original_message=message,
            copied_message=copied_message
        )
        
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
        if "USER_IS_BLOCKED" in str(e).upper() or "PEER_ID_INVALID" in str(e).upper():
             await client.send_message(Config.ADMIN_ID, "⚠️ **CRITICAL ERROR:** I could not access the Owner Database Channel.")
