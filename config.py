import os

class Config:
    # Your API details from my.telegram.org
    API_ID = int(os.environ.get("API_ID", "10389378"))
    API_HASH = os.environ.get("API_HASH", "cdd5c820cb6abeecaef38e2bb8db4860")

    # Your NEW bot token from @BotFather
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "7513275210:AAGgRzfVk1_nEaekouSY1kWmp0eqD3pNw-I")

    # Your admin user ID
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "7944526906"))

    # Your MongoDB Connection String
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://soniji:chaloji@cluster0.i5zy74f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "telegram_bot")
    
    # --- NEW: Invite Link for your Owner Database Channel ---
    # Create an invite link for your private database channel and paste it here.
    OWNER_DB_INVITE_LINK = os.environ.get("OWNER_DB_INVITE_LINK", "https://t.me/+NsSNh1Cx-Rk1M2Yx")
    
    # A default link for your shortener to use in the bot's PM.
    SHORTENER_AD_LINK = os.environ.get("SHORTENER_AD_LINK", "https://google.com")
