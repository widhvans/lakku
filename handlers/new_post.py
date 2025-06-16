import logging
import re
from pyrogram import Client, filters
from config import Config
from database.db import save_file_data, find_owner_by_db_channel
from utils.helpers import create_post

logger = logging.getLogger(__name__)

@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio), group=2)
async def new_file_handler(client, message):
    try:
        user_id = await find_owner_by_db_channel(message.chat.id)
        if not user_id: 
            return

        media = getattr(message, message.media.value, None)
        if not media or not getattr(media, 'file_name', None): return
        
        # This will now work because the admin has run /connect_db after starting the bot
        copied_message = await message.copy(chat_id=Config.OWNER_DATABASE_CHANNEL)
        
        await save_file_data(
            owner_id=user_id,
            original_message=message,
            copied_message=copied_message
        )
        
        # This is an example of a simple confirmation, can be expanded if needed
        # For high-frequency uploads, it's better to keep this silent
        # await client.send_message(user_id, f"✅ Indexed: `{media.file_name}`")
        
    except Exception as e:
        logger.exception("Error in new_file_handler")
        # If this fails, it's because the admin has not run /connect_db yet
        # or the bot was removed as an admin.
        error_message = (
            f"⚠️ **Action Required!**\n\nI failed to save a file to the Owner Database Channel (`{Config.OWNER_DATABASE_CHANNEL}`).\n"
            f"**Error:** `{e}`\n\n"
            "If this is a new bot or a new session, please send me the command `/connect_db` in my PM to fix this."
        )
        try:
            await client.send_message(chat_id=Config.ADMIN_ID, text=error_message)
        except Exception:
            logger.error("Could not send configuration error report to admin.")
