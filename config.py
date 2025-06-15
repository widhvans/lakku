# config.py

import os

class Config:
    """
    All configuration variables are stored in this class.
    The default values are filled from the details you provided.
    """

    # Your API details from my.telegram.org
    API_ID = int(os.environ.get("API_ID", "10389378"))
    API_HASH = os.environ.get("API_HASH", "cdd5c820cb6abeecaef38e2bb8db4860")

    # Your bot token from @BotFather
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "7513275210:AAGgRzfVk1_nEaekouSY1kWmp0eqD3pNw-I")

    # Your admin user ID
    # The bot will send start/stop notifications to this user.
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "1938030055"))

    # Your MongoDB Connection String
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://soniji:chaloji@cluster0.i5zy74f.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

    # Name of the database in MongoDB
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "telegram_bot")
    
    # Your shortener details
    SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "earn4link.in")
    SHORTLINK_API = os.environ.get("SHORTLINK_API", "987ef01cfd538490d733c3341926742e779421e2")
    
    # You can keep these extra variables if needed by other parts of the code
    ENABLE_SHORTLINK = True
    BOT_USERNAME = "@Complete_jwshw_bot"
