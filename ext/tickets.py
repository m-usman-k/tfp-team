import os
import motor.motor_asyncio
import traceback

class Tickets:

    def __init__(self):
        """Initialise the database."""
        db_key = os.getenv("DATABASE_KEY")
        if db_key is None:
            raise ValueError("Missing environment variable: 'DATABASE_KEY'")
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(db_key)
            self.db = self.client["tfp_team"]
            self.collection = self.db["tickets"]
            self.fs = motor.motor_asyncio.AsyncIOMotorGridFSBucket(self.db)
        except Exception as e:
            raise Exception("Error connecting to the database") from e

    async def close(self):
        """Close the database connection."""
        if self.client is not None:
            self.client.close()

    async def does_ticket_exist(self, ticket_id : int) -> bool:
        return await self.collection.count_documents({"_id": ticket_id}) > 0

    async def insert_ticket(self, ticket_id : int, user_id : int):
        try:
            if await self.does_ticket_exist(ticket_id):
                raise Exception(f"Ticket with ID {ticket_id} already exists!")

            await self.collection.insert_one(
                {
                    "_id": ticket_id,
                    "user_id": user_id
                }
            )
        except:
            traceback.print_exc()
    
    async def get_ticket(self, ticket_id : int) -> dict:
        if not await self.does_ticket_exist(ticket_id):
            raise Exception(f"Ticket with ID {ticket_id} does not exist on database!")
        return await self.collection.find_one({"_id": ticket_id})

    async def remove_ticket(self, ticket_id : int):
        try:
            if not await self.does_ticket_exist(ticket_id):
                return

            await self.collection.delete_one({"_id": ticket_id})
        except:
            traceback.print_exc()