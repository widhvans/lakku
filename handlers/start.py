import traceback
import logging
from pyrogram import Client, filters, enums
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.db import add_user, get_file_by_raw_link, get_user
from utils.helpers import get_main_menu, decode_link

logger = logging.getLogger(__name__)

async def send_file(client, user_id, raw_link):
    """A helper function to send the file after all checks are passed."""
    try:
        file_data = await get_file_by_raw_link(raw_link)
        if not file_data:
            return await client.send_message(user_id, "Sorry, this file is no longer available.")
        
        parts = raw_link.split("/")
        from_chat_id, message_id = int("-100" + parts[-2]), int(parts[-1])
        
        await client.copy_message(
            chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id,
            caption=f"**File:** `{file_data.get('file_name', 'N/A')}`"
        )
    except Exception:
        logger.exception("Error in send_file function")
        await client.send_message(user_id, "Something went wrong while sending the file.")

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if message.from_user.is_bot: return
    user_id = message.from_user.id
    await add_user(user_id)
    
    if len(message.command) > 1 and message.command[1].startswith("get_"):
        try:
            _, raw_link_encoded = message.command[1].split("_", 1)
            raw_link = decode_link(raw_link_encoded)
            file_data = await get_file_by_raw_link(raw_link)
            if not file_data: return await message.reply_text("File not found or link is invalid.")

            owner_id = file_data['owner_id']
            owner_settings = await get_user(owner_id)
            fsub_channel = owner_settings.get('fsub_channel')

            if fsub_channel:
                try:
                    member = await client.get_chat_member(chat_id=fsub_channel, user_id=user_id)
                    if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.RESTRICTED]:
                        raise UserNotParticipant
                except UserNotParticipant:
                    try: invite_link = await client.export_chat_invite_link(chat_id=fsub_channel)
                    except: invite_link = None
                    buttons = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]] if invite_link else []
                    buttons.append([InlineKeyboardButton("🔄 Retry", callback_data=f"retry_{message.command[1]}")])
                    return await message.reply_text("You must join the channel to get files.", reply_markup=InlineKeyboardMarkup(buttons))
            
            await send_file(client, user_id, raw_link)
        except Exception:
            logger.exception("Error processing deep link in /start")
            await message.reply_text("Something went wrong.")
    else:
        text = (
            f"Hello {message.from_user.mention}! 👋\n\n"
            "I am your personal **File Storage & Auto-Posting Bot**.\n\n"
            "✓ Save files to private channels.\n"
            "✓ Auto-post them to public channels.\n"
            "✓ Customize everything from captions to footers.\n\n"
            "Click the button below to begin!"
        )
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Let's Go 🚀", callback_data=f"go_back_{user_id}")]]))

@Client.on_callback_query(filters.regex(r"^retry_"))
async def retry_handler(client, query):
    user_id = query.from_user.id
    payload = query.data.split("_", 1)[1]
    
    # Directly re-check FSub and send the file, no need to re-call start_command
    try:
        await query.answer("Verifying...")
        _, raw_link_encoded = payload.split("_", 1)
        raw_link = decode_link(raw_link_encoded)
        file_data = await get_file_by_raw_link(raw_link)
        if not file_data: return await query.answer("Sorry, file not found.", show_alert=True)
        
        owner_id = file_data['owner_id']
        owner_settings = await get_user(owner_id)
        fsub_channel = owner_settings.get('fsub_channel')

        if fsub_channel:
            await client.get_chat_member(chat_id=fsub_channel, user_id=user_id)
        
        # If the check above passes without UserNotParticipant error, send the file
        await query.message.delete()
        await send_file(client, user_id, raw_link)

    except UserNotParticipant:
        await query.answer("You still haven't joined the channel. Please join and click Retry again.", show_alert=True)
    except Exception as e:
        logger.exception("Error in retry_handler")
        await query.answer("An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex(r"go_back_"))
async def go_back_callback(client, query):
    user_id = int(query.data.split("_")[-1])
    if query.from_user.id != user_id: return await query.answer("This is not for you!", show_alert=True)
    try:
        await query.message.edit_text("⚙️ Here are the main settings:", reply_markup=await get_main_menu(user_id))
    except MessageNotModified:
        await query.answer()
    except Exception as e:
        logger.exception("Error in go_back_callback")
