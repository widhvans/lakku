import logging
import re
from pyrogram import Client, filters
from database.db import find_owner_by_db_channel, save_file_data
from config import Config

logger = logging.getLogger(__name__)

@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio), group=2)
async def new_file_handler(client, message):
    try:
        user_id = await find_owner_by_db_channel(message.chat.id)
        if not user_id: return

        media = getattr(message, message.media.value, None)
        if not media or not getattr(media, 'file_name', None): return
        
        # If startup check failed, this will be None
        if not client.owner_db_channel_id:
            logger.warning("Owner DB not configured, cannot process file.")
            if user_id == Config.ADMIN_ID:
                await client.send_message(Config.ADMIN_ID, "⚠️ **Action Required!**\nI cannot save your file because the Owner Database is not configured or accessible. Please use the `Set Owner DB` button in my settings.")
            return
            
        # The copy operation is now safe because the startup check succeeded
        copied_message = await message.copy(chat_id=client.owner_db_channel_id)
        
        await save_file_data(
            owner_id=user_id,
            original_message=message,
            copied_message=copied_message
        )
        
        # No batching logic here anymore, it's all handled by the worker queue in bot.py
        await client.file_queue.put((copied_message, user_id))
        
    except Exception:
        logger.exception("Error in new_file_handler")
