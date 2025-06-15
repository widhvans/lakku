from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

client = AsyncIOMotorClient(Config.MONGO_URI)
db = client[Config.DATABASE_NAME]

users = db['users']
files = db['files']

async def add_user(user_id):
    user_data = {
        'user_id': user_id, 'post_channels': [], 'db_channels': [],
        'shortener_url': None, 'shortener_api': None, 'footer_text': None,
        'fsub_channel': None, 'custom_caption': None, 'footer_buttons': [],
        'show_poster': True, 'shortener_enabled': True
    }
    await users.update_one({'user_id': user_id}, {"$setOnInsert": user_data}, upsert=True)

# ... (The first few functions are unchanged) ...
async def get_user(user_id):
    return await users.find_one({'user_id': user_id})

async def get_all_user_ids(storage_owners_only=False):
    query = {}
    if storage_owners_only:
        query = {"$or": [
            {"post_channels": {"$exists": True, "$ne": []}},
            {"db_channels": {"$exists": True, "$ne": []}}
        ]}
    cursor = users.find(query, {'user_id': 1})
    return [doc['user_id'] for doc in await cursor.to_list(length=None) if 'user_id' in doc]

async def get_storage_owner_ids():
    query = {"$or": [
        {"post_channels": {"$exists": True, "$ne": []}},
        {"db_channels": {"$exists": True, "$ne": []}}
    ]}
    cursor = users.find(query, {'user_id': 1})
    return [doc['user_id'] for doc in await cursor.to_list(length=None) if 'user_id' in doc]

async def get_normal_user_ids():
    all_users_cursor = users.find({}, {'user_id': 1})
    storage_owners_cursor = users.find({
        "$or": [
            {"post_channels": {"$exists": True, "$ne": []}},
            {"db_channels": {"$exists": True, "$ne": []}}
        ]
    }, {'user_id': 1})
    all_user_ids = {doc['user_id'] for doc in await all_users_cursor.to_list(length=None) if 'user_id' in doc}
    storage_owner_ids = {doc['user_id'] for doc in await storage_owners_cursor.to_list(length=None) if 'user_id' in doc}
    normal_user_ids = all_user_ids - storage_owner_ids
    return list(normal_user_ids)

async def get_storage_owners_count():
    query = {"$or": [
        {"post_channels": {"$exists": True, "$ne": []}},
        {"db_channels": {"$exists": True, "$ne": []}}
    ]}
    return await users.count_documents(query)

async def update_user(user_id, key, value):
    await users.update_one({'user_id': user_id}, {'$set': {key: value}}, upsert=True)

async def add_to_list(user_id, list_name, item):
    await users.update_one({'user_id': user_id}, {'$addToSet': {list_name: item}})

async def remove_from_list(user_id, list_name, item):
    await users.update_one({'user_id': user_id}, {'$pull': {list_name: item}})

async def find_owner_by_db_channel(channel_id):
    user = await users.find_one({'db_channels': channel_id})
    return user['user_id'] if user else None

async def save_file_data(owner_id, message):
    from utils.helpers import get_file_raw_link
    media = getattr(message, message.media.value)
    raw_link = await get_file_raw_link(message)
    file_data = {
        'owner_id': owner_id, 'file_unique_id': media.file_unique_id,
        'file_id': media.file_id, 'file_name': media.file_name,
        'file_size': media.file_size, 'raw_link': raw_link
    }
    await files.update_one(
        {'owner_id': owner_id, 'file_unique_id': media.file_unique_id},
        {'$set': file_data}, upsert=True
    )

async def get_file_by_raw_link(link: str):
    return await files.find_one({'raw_link': link})

async def get_user_file_count(owner_id):
    return await files.count_documents({'owner_id': owner_id})

async def get_all_user_files(user_id):
    return files.find({'owner_id': user_id})

async def get_paginated_files(user_id, page: int, page_size: int = 5):
    skip = (page - 1) * page_size
    cursor = files.find({'owner_id': user_id}).sort('_id', -1).skip(skip).limit(page_size)
    return await cursor.to_list(length=page_size)

# --- NEW FUNCTION FOR USER-SPECIFIC SEARCH ---
async def search_user_files(user_id, query: str, page: int, page_size: int = 5):
    """Searches for files owned by a specific user and returns a paginated list."""
    search_filter = {'owner_id': user_id, 'file_name': {'$regex': query, '$options': 'i'}}
    skip = (page - 1) * page_size
    
    total_files = await files.count_documents(search_filter)
    cursor = files.find(search_filter).sort('_id', -1).skip(skip).limit(page_size)
    
    files_list = await cursor.to_list(length=page_size)
    return files_list, total_files
# ----------------------------------------------

async def search_files(query): # This is the universal search for inline mode
    if len(query) < 3: return []
    cursor = files.find(
        {'file_name': {'$regex': query, '$options': 'i'}},
        {'file_name': 1, 'file_size': 1, 'raw_link': 1, 'owner_id': 1, '_id': 0}
    )
    return await cursor.to_list(length=50)

async def total_users_count():
    return await users.count_documents({})

async def add_footer_button(user_id, button_name, button_url):
    button = {'name': button_name, 'url': button_url}
    await users.update_one({'user_id': user_id}, {'$push': {'footer_buttons': button}})

async def remove_footer_button(user_id, button_name):
    await users.update_one({'user_id': user_id}, {'$pull': {'footer_buttons': {'name': button_name}}})
