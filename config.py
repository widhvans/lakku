import os

class Config:
    API_ID = int(os.environ.get("API_ID", "10389378"))
    API_HASH = os.environ.get("API_HASH", "cdd5c820cb6abeecaef38e2bb8db4860")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "7513275210:AAGgRzfVk1_nEaekouSY1kWmp0eqD3pNw-I")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "1938030055"))

    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://soniji:chaloji@cluster0.i5zy74f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "telegram_bot")
    
    # --- Your main, private database channel ID ---
    # The bot MUST be an admin in this channel.
    OWNER_DATABASE_CHANNEL = int(os.environ.get("OWNER_DATABASE_CHANNEL", -1002832802347))
    
    # A default link for your shortener to use in the bot's PM.
    SHORTENER_AD_LINK = os.environ.get("SHORTENER_AD_LINK", "https://google.com")

    # The file that stores your bot's username for the web redirector
    BOT_USERNAME_FILE = "bot_username.txt"
    
    # Your VPS IP and Port for the web redirector
    VPS_IP = os.environ.get("VPS_IP", "65.21.183.36")
    VPS_PORT = int(os.environ.get("VPS_PORT", 7071))
