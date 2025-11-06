from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    """
    Manages active WebSocket connections for multiple staff members.
    """

    def __init__(self):
        # A dictionary that maps staff_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, staff_id: str, websocket: WebSocket):
        """
        Accepts a new websocket connection and stores it under the staff_id.
        """
        await websocket.accept()
        if staff_id not in self.active_connections:
            self.active_connections[staff_id] = []
        self.active_connections[staff_id].append(websocket)
        print(f"✅ Staff {staff_id} connected. Total connections: {len(self.active_connections[staff_id])}")

    def disconnect(self, staff_id: str, websocket: WebSocket):
        """
        Removes a websocket connection when a client disconnects.
        """
        if staff_id in self.active_connections:
            self.active_connections[staff_id].remove(websocket)
            if not self.active_connections[staff_id]:
                del self.active_connections[staff_id]
            print(f"❌ Staff {staff_id} disconnected.")

    async def send_personal_message(self, staff_id: str, message: dict):
        """
        Sends a direct message to all of a specific staff member's connections.
        (Useful if a staff logs in from multiple devices)
        """
        if staff_id in self.active_connections:
            for conn in self.active_connections[staff_id]:
                await conn.send_json(message)

    async def broadcast(self, staff_id: str, message: dict):
        """
        Broadcasts a message to all subscribers related to a specific staff_id.
        (e.g., for admin dashboards tracking multiple staff)
        """
        if staff_id in self.active_connections:
            for conn in self.active_connections[staff_id]:
                await conn.send_json(message)
