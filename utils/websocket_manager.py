from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    """
    Handles real-time location rooms per company.
    Each company room has staff and admin connections.
    Staff send location updates.
    Admins receive those updates in real-time.
    """

    def __init__(self):
        # { company_id: { "staff": {staff_id: websocket}, "admins": [websocket], "locations": {staff_id: location_data} } }
        self.rooms: Dict[str, Dict] = {}

    async def connect_staff(self, company_id: str, staff_id: str, websocket: WebSocket):
        await websocket.accept()
        if company_id not in self.rooms:
            self.rooms[company_id] = {"staff": {}, "admins": [], "locations": {}}
        self.rooms[company_id]["staff"][staff_id] = websocket
        print(f"✅ Staff {staff_id} connected to company {company_id}")

    def disconnect_staff(self, company_id: str, staff_id: str):
        if company_id in self.rooms and staff_id in self.rooms[company_id]["staff"]:
            del self.rooms[company_id]["staff"][staff_id]
            self.rooms[company_id]["locations"].pop(staff_id, None)
            print(f"❌ Staff {staff_id} disconnected from {company_id}")

    async def connect_admin(self, company_id: str, websocket: WebSocket):
        await websocket.accept()
        if company_id not in self.rooms:
            self.rooms[company_id] = {"staff": {}, "admins": [], "locations": {}}
        self.rooms[company_id]["admins"].append(websocket)
        print(f"👑 Admin joined company {company_id}")

    def disconnect_admin(self, company_id: str, websocket: WebSocket):
        if company_id in self.rooms and websocket in self.rooms[company_id]["admins"]:
            self.rooms[company_id]["admins"].remove(websocket)
            print(f"❌ Admin left company {company_id}")

    async def update_location(self, company_id: str, staff_id: str, data: dict):
        """
        Update staff location in memory and notify all admins.
        """
        if company_id in self.rooms:
            self.rooms[company_id]["locations"][staff_id] = data
            for admin_ws in self.rooms[company_id]["admins"]:
                await admin_ws.send_json({
                    "staff_id": staff_id,
                    "location": data
                })

    def get_staff_location(self, company_id: str, staff_id: str):
        """
        Returns the latest known location for a staff (if any).
        """
        room = self.rooms.get(company_id)
        if not room:
            return None
        return room["locations"].get(staff_id)
