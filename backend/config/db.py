from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise Exception("MONGO_URI not set in .env")
    client = MongoClient(mongo_uri)
    return client['test']  # your database name
