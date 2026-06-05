import json
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

client = MongoClient(os.environ["MONGODB_URI"])
db = client.get_database("video_generator")
videos = db.videos

doc = videos.find_one({"_id": ObjectId("6a117b402551d90cfcce5524")})

def json_serial(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

print(json.dumps(doc, default=json_serial, indent=2))
