import logging
from pyrogram import Client, filters
from database.db import find_owner_by_db_channel
from config import Config

logger = logging.getLogger(__name__)

@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio), group=2)
async def new_file_handler(client, message):
    try:
        user_id = await find_owner_by_db_channel(message.chat.id)
        if not user_id: 
            return

        media = getattr(message, message.media.value, None)
        if not media or not getattr(media, 'file_name', None):
            return
        
        if not client.owner_db_channel_id:
             logger.warning("Owner Database Channel not yet set up by admin. Ignoring file.")
             if user_id == Config.ADMIN_ID:
                 await client.send_message(Config.ADMIN_ID, "⚠️ **Setup Incomplete:** Please use the 'Set Owner DB' button in settings.")
             return
        
        await client.file_queue.put((message, user_id, client.owner_db_channel_id))
        logger.info(f"Added file '{media.file_name}' to the processing queue for user {user_id}.")

    except Exception:
        logger.exception("Error in new_file_handler while adding to queue")
