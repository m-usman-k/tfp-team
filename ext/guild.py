import os
import motor.motor_asyncio
import traceback
from typing import Literal

class Guilds:

    def __init__(self):
        """Initialise the database."""
        db_key = os.getenv("DATABASE_KEY")
        if db_key is None:
            raise ValueError("Missing environment variable: 'DATABASE_KEY'")
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(db_key)
            self.db = self.client["tfp_team"]
            self.collection = self.db["guilds"]
            self.fs = motor.motor_asyncio.AsyncIOMotorGridFSBucket(self.db)
        except Exception as e:
            raise Exception("Error connecting to the database") from e

    async def close(self):
        """Close the database connection."""
        if self.client is not None:
            self.client.close()

    async def does_guild_exist(self, guild_id : int) -> bool:
        return await self.collection.count_documents({"_id": guild_id}) > 0

    async def insert_guild(self, guild_id : int, order_channel : int, order_message : int):
        try:
            if await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} already exists!")

            await self.collection.insert_one(
                {
                    "_id": guild_id,
                    "order_channel": order_channel,
                    "order_message": order_message,
                    "notify": [],
                    "status": "Closed" #LITERAL "Closed", "Open", "Paused"
                }
            )
        except:
            traceback.print_exc()
    
    async def get_guild(self, guild_id : int) -> dict:
        if not await self.does_guild_exist(guild_id):
            raise Exception(f"Guild with ID {guild_id} does not exist on database!")
        return await self.collection.find_one({"_id": guild_id})

    async def update_order_channel(self, guild_id : int, channel_id : int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")

            await self.collection.update_one(
                {"_id": guild_id},
                {"$set": {"order_channel": channel_id}},
            )
        except:
            traceback.print_exc()
    
    async def update_order_message(self, guild_id : int, message_id : int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")

            await self.collection.update_one(
                {"_id": guild_id},
                {"$set": {"order_message": message_id}},
            )
        except:
            traceback.print_exc()
    
    async def update_status(self, guild_id : int, status : Literal["Open", "Closed", "Paused"]):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")

            await self.collection.update_one(
                {"_id": guild_id},
                {"$set": {"status": status}},
            )
        except:
            traceback.print_exc()
    
    async def add_notify(self, guild_id : int, user : int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")

            await self.collection.update_one(
                {"_id": guild_id},
                {"$push": {"notify": user}},
            )
        except:
            traceback.print_exc()

    async def remove_notify(self, guild_id : int, user : int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")

            await self.collection.update_one(
                {"_id": guild_id},
                {"$pull": {"notify": user}},
            )
        except:
            traceback.print_exc()
    
    async def clear_notifies(self, guild_id : int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")

            await self.collection.update_one(
                {"_id": guild_id},
                {"$set": {"notify": []}},
            )
        except:
            traceback.print_exc()