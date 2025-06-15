import traceback
import logging
from pyrogram import Client, filters, enums
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config
from database.db import add_user, get_file_by_raw_link, get_user
from utils.helpers import get_main_menu, decode_link, encode_link
from features.shortener import get_shortlink

logger = logging.getLogger(__name__)

async def send_file(client, user_id, raw_link):
    """Helper function to send the final file."""
    try:
        file_data = await get_file_by_raw_link(raw_link)
        if not file_data:
            return await client.send_message(user_id, "Sorry, this file is no longer available.")
        
        await client.copy_message(
            chat_id=user_id,
            from_chat_id=Config.OWNER_DATABASE_CHANNEL,
            message_id=file_data['file_id'],
            caption=f"**File:** `{file_data.get('file_name', 'N/A')}`"
        )
    except Exception:
        logger.exception("Error in send_file function")
        await client.send_message(user_id, "Something went wrong while sending the file. Please try again later.")

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if message.from_user.is_bot: return
    user_id = message.from_user.id
    await add_user(user_id)
    
    # Handle deep links for file requests
    if len(message.command) > 1 and message.command[1].startswith("get_"):
        try:
            payload = message.command[1]
            await handle_file_request(client, message, user_id, payload)
        except Exception:
            logger.exception("Error processing deep link in /start")
            await message.reply_text("Something went wrong.")
    else:
        # Restored professional start message
        text = (
            f"Hello {message.from_user.mention}! 👋\n\n"
            "I am your personal **File Storage & Auto-Posting Bot**.\n\n"
            "**My Features:**\n"
            "✓ Save files to private channels.\n"
            "✓ Auto-post them to public channels.\n"
            "✓ Customize everything from captions to footers.\n\n"
            "Click the button below to begin!"
        )
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Let's Go 🚀", callback_data=f"go_back_{user_id}")]]))

async def handle_file_request(client, message, user_id, payload):
    """Contains the full logic for FSub and showing the shortener link."""
    raw_link_encoded = payload.split("_", 1)[1]
    raw_link = decode_link(raw_link_encoded)
    file_data = await get_file_by_raw_link(raw_link)
    if not file_data: return await message.reply_text("File not found.")

    owner_id = file_data['owner_id']
    owner_settings = await get_user(owner_id)
    fsub_channel = owner_settings.get('fsub_channel')

    if fsub_channel:
        try:
            member = await client.get_chat_member(chat_id=fsub_channel, user_id=user_id)
            if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.RESTRICTED]:
                raise UserNotParticipant
        except UserNotParticipant:
            try: invite_link = await client.export_chat_invite_link(fsub_channel)
            except: invite_link = None
            buttons = [[InlineKeyboardButton("📢 Join Channel", url=invite_link)]] if invite_link else []
            buttons.append([InlineKeyboardButton("🔄 Retry", callback_data=f"retry_{payload}")])
            return await message.reply_text("You must join the channel to continue.", reply_markup=InlineKeyboardMarkup(buttons))
    
    # If FSub is passed, show the shortener link
    shortened_link = await get_shortlink(Config.SHORTENER_AD_LINK, owner_id)
    final_payload = f"finalget_{raw_link_encoded}"
    
    await message.reply_text(
        "Please complete the task in the link below to get your file.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➡️ Click here to complete task", url=shortened_link)],
            [InlineKeyboardButton("✅ Get File", callback_data=final_payload)]
        ])
    )

@Client.on_callback_query(filters.regex(r"^finalget_"))
async def final_get_handler(client, query):
    # User has completed shortener and clicks "Get File"
    raw_link_encoded = query.data.split("_", 1)[1]
    raw_link = decode_link(raw_link_encoded)
    await query.message.delete()
    await send_file(client, query.from_user.id, raw_link)

@Client.on_callback_query(filters.regex(r"^retry_"))
async def retry_handler(client, query):
    await query.message.delete()
    # Re-run the file request logic after user clicks retry
    await handle_file_request(client, query.message, query.from_user.id, query.data.split("_", 1)[1])

@Client.on_callback_query(filters.regex(r"go_back_"))
async def go_back_callback(client, query):
    user_id = int(query.data.split("_")[-1])
    if query.from_user.id != user_id: return await query.answer("This is not for you!", show_alert=True)
    try:
        await query.message.edit_text("⚙️ Here are the main settings:", reply_markup=await get_main_menu(user_id))
    except MessageNotModified:
        await query.answer()
