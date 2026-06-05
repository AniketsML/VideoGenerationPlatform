import asyncio
import json
from app.database import videos_collection
from bson import ObjectId

async def main():
    print("Fetching last 10 videos...")
    cursor = videos_collection.find().sort("_id", -1)
    docs = await cursor.to_list(length=10)
    for idx, doc in enumerate(docs):
        print(f"\n--- Video {idx + 1} ---")
        print(f"ID: {doc.get('_id')}")
        print(f"Video ID: {doc.get('job_data', {}).get('video_id') or doc.get('result_payload', {}).get('video_id')}")
        print(f"Status: {doc.get('status')}")
        print(f"Video Type / Mode: {doc.get('request_mode')}")
        print(f"Video URL: {doc.get('video_url')}")
        print(f"Created At: {doc.get('created_at')}")

if __name__ == "__main__":
    asyncio.run(main())
