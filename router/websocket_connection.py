from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.websocket_manager import ConnectionManager
import asyncio, json
from utils.location import get_location_details
import os

router = APIRouter()
manager = ConnectionManager()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


@router.websocket("/ws/location/{staff_id}")
async def location_updates(websocket: WebSocket, staff_id: str):
    print("it works")
    print(f"Incoming connection from staff_id={staff_id}")
    await manager.connect(staff_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            latitude = payload.get("latitude")
            longitude = payload.get("longitude")

            location_details = get_location_details(latitude, longitude, GOOGLE_API_KEY)

            response = {
                "staff_id": staff_id,
                "latitude": latitude,
                "longitude": longitude,
                "location": location_details,
            }

            await websocket.send_json({
                "status": "success",
                "message": "Location updated successfully",
                **response
            })

            await manager.broadcast(staff_id, response)
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(staff_id, websocket)
