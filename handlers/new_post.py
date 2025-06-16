import logging
import re
from pyrogram import Client, filters
from config import Config
from database.db import find_owner_by_db_channel

logger = logging.getLogger(__name__)

@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio), group=2)
async def new_file_handler(client, message):
    """
    This handler now attempts to process the file directly.
    If it fails, it provides a clear, actionable error message to the admin.
    """
    try:
        user_id = await find_owner_by_db_channel(message.chat.id)
        if not user_id: 
            return

        media = getattr(message, message.media.value, None)
        if not media or not getattr(media, 'file_name', None):
            return
        
        # Add the message to the central queue for the worker to process
        await client.file_queue.put((message, user_id))
        
    except Exception as e:
        logger.exception("Error in new_file_handler while adding to queue")
