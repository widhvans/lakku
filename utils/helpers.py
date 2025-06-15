import re
import base64
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import get_user
from features.poster import get_poster

# (Most functions are unchanged, only create_post is modified)

async def create_post(client, user_id, messages):
    user = await get_user(user_id)
    if not user: return None, None, None
    bot_username = client.me.username
    title, year = clean_filename(getattr(messages[0], messages[0].media.value).file_name)
    caption_header = f"🎬 **{title} {f'({year})' if year else ''}**"
    
    links = ""
    messages.sort(key=lambda m: getattr(m, m.media.value).file_name)
    
    for msg in messages:
        media = getattr(msg, msg.media.value)
        link_label = re.sub(r'\[@.*?\]', '', media.file_name).strip()
        raw_link = await get_file_raw_link(msg)
        
        # --- NEW: Generate a direct bot link, NOT a shortened one ---
        payload = f"get_{encode_link(raw_link)}"
        bot_redirect_link = f"https://t.me/{bot_username}?start={payload}"
        # The shortener is no longer called here
        
        links += f"📁 `{link_label}`\n\n[🔗 Click Here]({bot_redirect_link})\n\n"
        
    custom_caption = f"\n{user.get('custom_caption', '')}" if user.get('custom_caption') else ""
    final_caption = f"{caption_header}\n\n{links}{custom_caption}"
    
    post_poster = await get_poster(title, year) if user.get('show_poster', True) else None
    
    footer_buttons_data = user.get('footer_buttons', [])
    footer_keyboard = None
    if footer_buttons_data:
        buttons = [[InlineKeyboardButton(btn['name'], url=btn['url'])] for btn in footer_buttons_data]
        footer_keyboard = InlineKeyboardMarkup(buttons)
        
    return post_poster, final_caption, footer_keyboard

# (Keep all other functions like get_main_menu, clean_filename, etc. from your provided foundation code)
async def get_main_menu(user_id):
    user_settings = await get_user(user_id)
    if not user_settings: return InlineKeyboardMarkup([])
    shortener_text = "⚙️ Shortener Settings" if user_settings.get('shortener_url') else "🔗 Set Shortener"
    fsub_text = "⚙️ Manage FSub" if user_settings.get('fsub_channel') else "📢 Set FSub"
    buttons = [
        [InlineKeyboardButton("➕ Manage Auto Post", callback_data="manage_post_ch")],
        [InlineKeyboardButton("🗃️ Manage Index DB", callback_data="manage_db_ch")],
        [InlineKeyboardButton(shortener_text, callback_data="shortener_menu"), InlineKeyboardButton("🔄 Backup Links", callback_data="backup_links")],
        [InlineKeyboardButton("✍️ Manage Caption", callback_data="caption_menu"), InlineKeyboardButton("👣 Footer Buttons", callback_data="manage_footer")],
        [InlineKeyboardButton("🖼️ IMDb Poster", callback_data="poster_menu"), InlineKeyboardButton("📂 My Files", callback_data="my_files_1")],
        [InlineKeyboardButton(fsub_text, callback_data="set_fsub")]
    ]
    return InlineKeyboardMarkup(buttons)

def go_back_button(user_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("« Go Back", callback_data=f"go_back_{user_id}")]])

def format_bytes(size):
    if not isinstance(size, (int, float)): return "N/A"
    power = 1024; n = 0; power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size >= power and n < len(power_labels) - 1 :
        size /= power; n += 1
    return f"{size:.2f} {power_labels[n]}"

async def get_file_raw_link(message):
    return f"https://t.me/c/{str(message.chat.id).replace('-100', '')}/{message.id}"

def encode_link(link: str) -> str:
    return base64.urlsafe_b64encode(link.encode()).decode().strip("=")

def decode_link(encoded_link: str) -> str:
    padding = 4 - (len(encoded_link) % 4)
    encoded_link += "=" * padding
    return base64.urlsafe_b64decode(encoded_link).decode()
