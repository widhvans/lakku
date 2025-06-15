import asyncio
import re
import logging
from pyrogram import Client, filters
from database.db import find_owner_by_db_channel

logger = logging.getLogger(__name__)

def get_batch_key(filename: str):
    """
    This function creates a common name for related files to be batched together.
    It is now called by the worker in bot.py.
    """
    name = re.sub(r'\.\w+$', '', filename)
    name = re.sub(r'[\._]', ' ', name)
    delimiters = [
        r'S\d{1,2}', r'Season\s?\d{1,2}', r'Part\s?\d{1,2}', r'E\d{1,3}', r'EP\d{1,3}',
        r'\b(19|20)\d{2}\b', r'\b(4k|2160p|1080p|720p|480p)\b', r'\[.*?\]'
    ]
    match = re.search('|'.join(delimiters), name, re.I)
    base_name = name[:match.start()].strip() if match else name.strip()
    return re.sub(r'\s+', ' ', base_name).lower()


@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio), group=2)
async def new_file_handler(client, message):
    """
    This handler is now very lightweight. It just finds the owner
    and adds the message to the central processing queue.
    """
    try:
        user_id = await find_owner_by_db_channel(message.chat.id)
        if not user_id: 
            return

        media = getattr(message, message.media.value, None)
        if not media or not getattr(media, 'file_name', None):
            return
        
        # Add the message and its owner to the queue for the worker to process
        await client.file_queue.put((message, user_id))
        logger.info(f"Added file '{media.file_name}' to the processing queue for user {user_id}.")

    except Exception:
        logger.exception("Error in new_file_handler while adding to queue")
