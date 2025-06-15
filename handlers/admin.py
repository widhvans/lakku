import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.db import total_users_count, get_all_user_ids, get_storage_owners_count, get_storage_owner_ids, get_normal_user_ids
from features.broadcaster import broadcast_message

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("stats") & filters.user(Config.ADMIN_ID))
async def stats_handler(_, message):
    try:
        total = await total_users_count()
        storage_owners = await get_storage_owners_count()
        
        text = (
            "📊 **Bot Statistics**\n\n"
            f"**Total Users:** `{total}`\n"
            f"**Storage Owners:** `{storage_owners}`\n"
            f"_(Storage Owners are users who have set at least one channel)_"
        )
        await message.reply_text(text)
    except Exception:
        logger.exception("Error in /stats handler")
        await message.reply_text("An error occurred while fetching stats.")

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN_ID))
async def broadcast_prompt_handler(client, message):
    if not message.reply_to_message:
        return await message.reply_text("Please reply to a message to start a broadcast.")
    
    message_to_broadcast_id = message.reply_to_message.id
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("To All Users 📣", callback_data=f"bcast_all_{message_to_broadcast_id}")],
        [InlineKeyboardButton("To Storage Owners Only 🗃️", callback_data=f"bcast_storage_{message_to_broadcast_id}")],
        [InlineKeyboardButton("To Normal Users Only 👤", callback_data=f"bcast_normal_{message_to_broadcast_id}")]
    ])
    await message.reply_text("Who should receive this broadcast?", reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"bcast_(all|storage|normal)_(\d+)") & filters.user(Config.ADMIN_ID))
async def broadcast_callback_handler(client, query):
    try:
        broadcast_type, message_id_str = query.data.split("_")[1:]
        message_id = int(message_id_str)

        await query.message.edit_text("Fetching user list... Please wait.")
        
        message_to_broadcast = await client.get_messages(chat_id=query.message.chat.id, message_ids=message_id)
        if not message_to_broadcast:
            return await query.message.edit_text("Error: Could not find the original message.")

        if broadcast_type == "all":
            user_ids = await get_all_user_ids()
        elif broadcast_type == "storage":
            user_ids = await get_storage_owner_ids()
        else: # broadcast_type == "normal"
            user_ids = await get_normal_user_ids()
        
        status_msg = await query.message.edit_text(f"Broadcasting to {len(user_ids)} users...")
        success, fail = await broadcast_message(client, user_ids, message_to_broadcast)
        await status_msg.edit_text(f"✅ **Broadcast Complete**\n\nSent to: `{success}` users.\nFailed for: `{fail}` users.")
    except Exception:
        logger.exception("Error in broadcast_callback_handler")
        await query.message.edit_text("An error occurred during broadcast.")
