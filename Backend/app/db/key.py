from typing import Optional
from pymongo.database import Database
from pymongo.collection import Collection
from loguru import logger
from app.model.key import KeyModel

def _get_collection(mongo_db: Database, name: str) -> Collection:
    if mongo_db is None:
        raise RuntimeError("Database connection not initialized — pass a valid mongo_db")
    return mongo_db.get_collection(name)

# Function to insert/update encrypted DEK into the MongoDB collection with validation.
async def insert_dek(key_data: dict, mongo_db: Database = None) -> bool:
    """
    Insert/update a encrypted DEK.
    Returns boolean
    """
    collection = _get_collection(mongo_db, "keys")
    try: 
        key = KeyModel(**key_data)
    except Exception as e:
        logger.error("Validation error:", e)
        return False

    filter = {"service_name": key.service_name, "userid": key.userid}
    update = {"$set": key.model_dump()}
    try:
        result = await collection.update_one(filter, update, upsert=True)
    except Exception as e:
        logger.error("Upsert error: {}", e)
        return False

    return True

# Function to retrieve encrypted DEK from the MongoDB collection.
async def get_dek(service_name: str, userid: str, mongo_db: Database = None) -> Optional[str]:
    """
    Retrieve encrypted DEK by service_name and userid.
    Returns dek string or None if not found.
    """
    collection = _get_collection(mongo_db, "keys")
    document = await collection.find_one({"service_name": service_name, "userid": userid})
    if document:
        return document.get("dek")
    return None

# Function to get the api_key services that belong to a user
async def get_api_services(userid:str, mongo_db: Database):
    collection = _get_collection(mongo_db,userid)
    results = await collection.find({"userid": userid})
    if results:
        return [result.get("service_name") for result in results]
    return None 

# Function to delete encrypted DEK from the MongoDB collection.
async def delete_api_key(userid: str, service_name: str, mongo_db: Database = None) -> bool:
    """
    Delete encrypted DEK by service_name and userid.
    Returns boolean indicating success.
    """
    collection = _get_collection(mongo_db, "keys")
    result = await collection.delete_one({"service_name": service_name, "userid": userid})
    return result.deleted_count > 0
