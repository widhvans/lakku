
import os

class Config:
    API_ID = int(os.environ.get("API_ID", "10389378"))
    API_HASH = os.environ.get("API_HASH", "cdd5c820cb6abeecaef38e2bb8db4860")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "7320891454:AAHp3AAIZK2RKIkWyYIByB_fSEq9Xuk9-bk")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "1938030055"))

    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://soniji:chaloji@cluster0.i5zy74f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "telegram_bot")
    
    # A default link for your shortener to use in the bot's PM.
    SHORTENER_AD_LINK = os.environ.get("SHORTENER_AD_LINK", "https://google.com")
