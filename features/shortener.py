import aiohttp
import logging
from database.db import get_user

logger = logging.getLogger(__name__)

async def get_shortlink(link, user_id):
    user = await get_user(user_id)
    if not user or not user.get('shortener_enabled') or not user.get('shortener_url'):
        return link

    URL = user['shortener_url'].strip()
    API = user['shortener_api'].strip()

    try:
        url = f'https://{URL}/api'
        params = {'api': API, 'url': link}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                data = await response.json(content_type=None)
                if data.get("status") == "success" and data.get("shortenedUrl"):
                    return data["shortenedUrl"]
                else:
                    logger.error(f"Shortener error for user {user_id}: {data.get('message', 'Unknown error')}")
                    return link
    except Exception as e:
        logger.error(f"HTTP Error during shortening for user {user_id}: {e}")
        return link
