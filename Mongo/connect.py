import os
from pymongo import MongoClient


def get_mongo_db(uri: str = None, db_name: str = None):
    mongo_uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    target_db = db_name or os.getenv("MONGO_DB", "scouts_db")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[target_db]



