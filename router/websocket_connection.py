from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.websocket_manager import ConnectionManager
import asyncio, json
from utils.location import get_location_details
import os

router = APIRouter()
manager = ConnectionManager()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


@router.websocket("/ws/staff/{company_id}/{staff_id}")
async def staff_location_ws(websocket: WebSocket, company_id: str, staff_id: str):
    await manager.connect_staff(company_id, staff_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            latitude = data.get("latitude")
            longitude = data.get("longitude")

            location_data = {
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": data.get("timestamp")
            }

            # Update location and notify admins
            await manager.update_location(company_id, staff_id, location_data)

    except WebSocketDisconnect:
        manager.disconnect_staff(company_id, staff_id)


@router.websocket("/ws/admin/{company_id}")
async def admin_ws(websocket: WebSocket, company_id: str):
    await manager.connect_admin(company_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Optionally handle requests like “get staff location”
            payload = json.loads(data)
            staff_id = payload.get("staff_id")

            staff_location = manager.get_staff_location(company_id, staff_id)
            if staff_location:
                await websocket.send_json({
                    "status": "success",
                    "staff_id": staff_id,
                    "location": staff_location
                })
            else:
                await websocket.send_json({
                    "status": "error",
                    "message": f"Staff {staff_id} not online or no location found."
                })
    except WebSocketDisconnect:
        manager.disconnect_admin(company_id, websocket)
