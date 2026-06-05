import asyncio
import os
import sys
from app.database import users_collection
from app.auth import get_password_hash

async def create_user():
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("ADMIN_PASSWORD", "changeme")
    normalized_email = email.strip().lower()
    
    print(f"Checking if user {normalized_email} exists...")
    existing_user = await users_collection.find_one({"email": normalized_email})
    if existing_user:
        print(f"User {normalized_email} already exists in database.")
        # Let's update password anyway to be sure
        hashed_password = get_password_hash(password)
        await users_collection.update_one(
            {"email": normalized_email},
            {"$set": {"hashed_password": hashed_password}}
        )
        print("Updated password successfully.")
        return
        
    hashed_password = get_password_hash(password)
    user_dict = {
        "email": normalized_email,
        "full_name": os.environ.get("ADMIN_FULL_NAME", "Admin"),
        "username": os.environ.get("ADMIN_USERNAME", "admin"),
        "hashed_password": hashed_password,
        "is_admin": True
    }
    
    await users_collection.insert_one(user_dict)
    print(f"Successfully created user: {normalized_email} with password: {password}")

if __name__ == "__main__":
    asyncio.run(create_user())
