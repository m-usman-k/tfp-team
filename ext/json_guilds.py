import os
import json
import aiofiles
import traceback
from typing import Literal

class Guilds:
    
    def __init__(self):
        """Initialize the JSON-based storage."""
        self.data_dir = "data"
        self.file_path = os.path.join(self.data_dir, "guilds.json")
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # Create empty JSON file if it doesn't exist
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)
    
    async def _load_data(self) -> dict:
        """Load data from JSON file."""
        try:
            async with aiofiles.open(self.file_path, 'r') as f:
                content = await f.read()
                return json.loads(content) if content else {}
        except Exception as e:
            print(f"Error loading guilds data: {e}")
            return {}
    
    async def _save_data(self, data: dict):
        """Save data to JSON file."""
        try:
            async with aiofiles.open(self.file_path, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error saving guilds data: {e}")
            traceback.print_exc()
    
    async def close(self):
        """Close method for compatibility (no-op for JSON storage)."""
        pass
    
    async def does_guild_exist(self, guild_id: int) -> bool:
        data = await self._load_data()
        return str(guild_id) in data
    
    async def insert_guild(self, guild_id: int, order_channel: int, order_message: int, category_id: int):
        try:
            if await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} already exists!")
            
            data = await self._load_data()
            data[str(guild_id)] = {
                "_id": guild_id,
                "order_channel": order_channel,
                "order_message": order_message,
                "category_id": category_id,
                "ticket_limit": 0,
                "tickets_today": 0,
                "last_reset": "",
                "notify": [],
                "status": "Closed"  # LITERAL "Closed", "Open", "Paused"
            }
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def get_guild(self, guild_id: int) -> dict:
        if not await self.does_guild_exist(guild_id):
            raise Exception(f"Guild with ID {guild_id} does not exist on database!")
        data = await self._load_data()
        return data[str(guild_id)]
    
    async def update_order_channel(self, guild_id: int, channel_id: int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            data[str(guild_id)]["order_channel"] = channel_id
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def update_order_message(self, guild_id: int, message_id: int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            data[str(guild_id)]["order_message"] = message_id
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def update_status(self, guild_id: int, status: Literal["Open", "Closed", "Paused"]):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            data[str(guild_id)]["status"] = status
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def add_notify(self, guild_id: int, user: int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            if user not in data[str(guild_id)]["notify"]:
                data[str(guild_id)]["notify"].append(user)
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def remove_notify(self, guild_id: int, user: int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            if user in data[str(guild_id)]["notify"]:
                data[str(guild_id)]["notify"].remove(user)
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def clear_notifies(self, guild_id: int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            data[str(guild_id)]["notify"] = []
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def increment_tickets_today(self, guild_id: int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            data[str(guild_id)]["tickets_today"] = data[str(guild_id)].get("tickets_today", 0) + 1
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def set_ticket_limit(self, guild_id: int, limit: int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            data[str(guild_id)]["ticket_limit"] = limit
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def set_tickets_today(self, guild_id: int, amount: int):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            data[str(guild_id)]["tickets_today"] = amount
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def reset_daily_tickets(self, guild_id: int, date_str: str):
        try:
            if not await self.does_guild_exist(guild_id):
                raise Exception(f"Guild with ID {guild_id} does not exist on database!")
            
            data = await self._load_data()
            data[str(guild_id)]["tickets_today"] = 0
            data[str(guild_id)]["last_reset"] = date_str
            await self._save_data(data)
        except:
            traceback.print_exc()
