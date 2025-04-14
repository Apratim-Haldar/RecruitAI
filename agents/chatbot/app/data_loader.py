from pymongo import MongoClient
from app.config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["GENAI"]

def load_candidates():
    return list(db["applications"].find({}))

def load_job_posts():
    return list(db["jobposts"].find({}))

