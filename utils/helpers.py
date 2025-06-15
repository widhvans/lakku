import re
import base64
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.db import get_user
from features.poster import get_poster
from features.shortener import get_shortlink

async def get_main_menu(user_id):
    user_settings = await get_user(user_id)
    if not user_settings: return InlineKeyboardMarkup([])

    shortener_text = "⚙️ Shortener Settings" if user_settings.get('shortener_url') else "🔗 Set Shortener"
    fsub_text = "⚙️ Manage FSub" if user_settings.get('fsub_channel') else "📢 Set FSub"
    
    # --- Corrected button layout with "How to Download" added back ---
    buttons = [
        [InlineKeyboardButton("➕ Manage Auto Post", callback_data="manage_post_ch")],
        [InlineKeyboardButton("🗃️ Manage Index DB", callback_data="manage_db_ch")],
        [
            InlineKeyboardButton(shortener_text, callback_data="shortener_menu"),
            InlineKeyboardButton("🔄 Backup Links", callback_data="backup_links")
        ],
        [
            InlineKeyboardButton("✍️ Manage Caption", callback_data="caption_menu"),
            InlineKeyboardButton("👣 Footer Buttons", callback_data="manage_footer")
        ],
        [
            InlineKeyboardButton("🖼️ IMDb Poster", callback_data="poster_menu"),
            InlineKeyboardButton("📂 My Files", callback_data="my_files_1")
        ],
        [
            InlineKeyboardButton(fsub_text, callback_data="set_fsub"),
            InlineKeyboardButton("❓ Set 'How to Download'", callback_data="set_download")
        ]
    ]
    
    if user_id == Config.ADMIN_ID:
        buttons.append([InlineKeyboardButton("🔑 Set Owner DB", callback_data="set_owner_db")])
        buttons.append([InlineKeyboardButton("⚠️ Reset Files DB", callback_data="reset_db_prompt")])
        
    return InlineKeyboardMarkup(buttons)

def go_back_button(user_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("« Go Back", callback_data=f"go_back_{user_id}")]])

# (The rest of the helper functions are unchanged and correct)
def format_bytes(size):
    if not isinstance(size, (int, float)): return "N/A"
    power = 1024; n = 0; power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size >= power and n < len(power_labels) - 1 :
        size /= power; n += 1
    return f"{size:.2f} {power_labels[n]}"

async def get_file_raw_link(message):
    return f"https://t.me/c/{str(message.chat.id).replace('-100', '')}/{message.id}"

def clean_filename(name: str):
    if not name: return "Untitled", None
    name = re.sub(r'\[@.*?\]', '', name)
    cleaned_name = re.sub(r'\.\w+$', '', name)
    cleaned_name = re.sub(r'[\._]', ' ', cleaned_name)
    year_match = re.search(r'\b(19|20)\d{2}\b', cleaned_name)
    year = year_match.group(0) if year_match else None
    if year: cleaned_name = cleaned_name.split(year)[0]
    cleaned_name = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', cleaned_name)
    tags_to_remove = [
        '1080p', '720p', '480p', '2160p', '4k', 'HD', 'FHD', 'UHD', 'BluRay', 'WEBRip', 'WEB-DL',
        'HDRip', 'x264', 'x265', 'HEVC', 'AAC', 'Dual Audio', 'Hindi', 'English', 'Esubs',
        r'S\d+E\d+', r'S\d+', r'Season\s?\d+', r'Part\s?\d+', r'E\d+', r'EP\d+'
    ]
    for tag in tags_to_remove:
        cleaned_name = re.sub(r'\b' + tag + r'\b', '', cleaned_name, flags=re.I)
    final_title = re.sub(r'\s+', ' ', cleaned_name).strip()
    if not final_title:
        final_title = re.sub(r'\.\w+$', '', name).replace(".", " ")
    return (f"{final_title} {year}".strip() if year else final_title), year

def encode_link(link: str) -> str:
    return base64.urlsafe_b64encode(link.encode()).decode().strip("=")

def decode_link(encoded_link: str) -> str:
    padding = 4 - (len(encoded_link) % 4)
    encoded_link += "=" * padding
    return base64.urlsafe_b64decode(encoded_link).decode()

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
        payload = f"get_{encode_link(raw_link)}"
        bot_redirect_link = f"https://t.me/{bot_username}?start={payload}"
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
