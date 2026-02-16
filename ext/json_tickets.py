import os
import json
import aiofiles
import traceback

class Tickets:
    
    def __init__(self):
        """Initialize the JSON-based storage."""
        self.data_dir = "data"
        self.file_path = os.path.join(self.data_dir, "tickets.json")
        
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
            print(f"Error loading tickets data: {e}")
            return {}
    
    async def _save_data(self, data: dict):
        """Save data to JSON file."""
        try:
            async with aiofiles.open(self.file_path, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error saving tickets data: {e}")
            traceback.print_exc()
    
    async def close(self):
        """Close method for compatibility (no-op for JSON storage)."""
        pass
    
    async def does_ticket_exist(self, ticket_id: int) -> bool:
        data = await self._load_data()
        return str(ticket_id) in data
    
    async def insert_ticket(self, ticket_id: int, user_id: int):
        try:
            if await self.does_ticket_exist(ticket_id):
                raise Exception(f"Ticket with ID {ticket_id} already exists!")
            
            data = await self._load_data()
            data[str(ticket_id)] = {
                "_id": ticket_id,
                "user_id": user_id
            }
            await self._save_data(data)
        except:
            traceback.print_exc()
    
    async def get_ticket(self, ticket_id: int) -> dict:
        if not await self.does_ticket_exist(ticket_id):
            raise Exception(f"Ticket with ID {ticket_id} does not exist on database!")
        data = await self._load_data()
        return data[str(ticket_id)]
    
    async def remove_ticket(self, ticket_id: int):
        try:
            if not await self.does_ticket_exist(ticket_id):
                return
            
            data = await self._load_data()
            del data[str(ticket_id)]
            await self._save_data(data)
        except:
            traceback.print_exc()
