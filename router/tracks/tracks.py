from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
import json
import asyncio
import requests
import os
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

router = APIRouter(
    prefix="/api/v1/tracks",
    tags=["tracks"]
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Helper Function ---
def get_location_details(latitude: float, longitude: float, google_api_key: str):
    """Use Google Maps API to convert lat/lon to readable address."""
    location_details = {}

    if latitude is not None and longitude is not None:
        try:
            geo_url = (
                f"https://maps.googleapis.com/maps/api/geocode/json"
                f"?latlng={latitude},{longitude}&key={google_api_key}"
            )
            response = requests.get(geo_url)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                components = result.get("address_components", [])

                location_details = {
                    "country": next((c["long_name"] for c in components if "country" in c["types"]), None),
                    "state": next((c["long_name"] for c in components if "administrative_area_level_1" in c["types"]), None),
                    "city": next((c["long_name"] for c in components if "locality" in c["types"]
                                  or "administrative_area_level_2" in c["types"]), None),
                    "formatted": result.get("formatted_address"),
                }
            else:
                location_details = {"formatted": "Unknown location"}

        except Exception as geo_error:
            print(f"Google Maps API error: {geo_error}")
            location_details = {"formatted": "Unknown location"}

    return location_details


# --- Connection Management ---
active_connections: Dict[str, List[WebSocket]] = {}

def add_connection(staff_id: str, websocket: WebSocket):
    """Add a websocket connection for a staff member."""
    active_connections.setdefault(staff_id, []).append(websocket)

def remove_connection(staff_id: str, websocket: WebSocket):
    """Remove a websocket connection."""
    if staff_id in active_connections:
        active_connections[staff_id].remove(websocket)
        if not active_connections[staff_id]:
            del active_connections[staff_id]

async def broadcast(staff_id: str, message: dict):
    """Broadcast message to all connected clients (admin dashboards, etc.)."""
    if staff_id in active_connections:
        for conn in list(active_connections[staff_id]):
            try:
                await conn.send_json(message)
            except Exception:
                await conn.close()
                remove_connection(staff_id, conn)


# --- WebSocket Endpoint ---
@router.websocket("/ws/location/{staff_id}")
async def location_updates(websocket: WebSocket, staff_id: str):
    """
    Receive real-time location updates every 10 seconds from staff devices.
    """
    await websocket.accept()
    add_connection(staff_id, websocket)
    print(f"✅ Staff {staff_id} connected to location stream.")

    try:
        while True:
            # Wait for data from client
            data = await websocket.receive_text()
            payload = json.loads(data)

            latitude = payload.get("latitude")
            longitude = payload.get("longitude")

            if not latitude or not longitude:
                await websocket.send_json({
                    "status": "error",
                    "message": "Latitude and longitude required."
                })
                continue

            location_details = get_location_details(latitude, longitude, GOOGLE_API_KEY)

            response = {
                "staff_id": staff_id,
                "latitude": latitude,
                "longitude": longitude,
                "location": location_details,
                "timestamp": asyncio.get_event_loop().time(),
            }

            # Send confirmation to client
            await websocket.send_json({
                "status": "success",
                "message": "Location updated successfully",
                **response
            })

            # Broadcast to others (admins or trackers)
            await broadcast(staff_id, response)

            # Wait before next expected update
            await asyncio.sleep(10)

    except WebSocketDisconnect:
        print(f"⚠️ Staff {staff_id} disconnected.")
        remove_connection(staff_id, websocket)
    except Exception as e:
        print(f"❌ Error in WebSocket for {staff_id}: {e}")
        remove_connection(staff_id, websocket)
        await websocket.close()


# --- REST Endpoint for On-Demand Location ---
@router.get("/{staff_id}/location")
async def get_staff_location(
    staff_id: str,
    latitude: float = Query(..., description="Staff's current latitude"),
    longitude: float = Query(..., description="Staff's current longitude")
):
    """
    Retrieve the exact location of a staff using latitude and longitude.
    """
    try:
        if not GOOGLE_API_KEY:
            raise HTTPException(status_code=500, detail="Google API key not configured")

        location = get_location_details(latitude, longitude, GOOGLE_API_KEY)

        return {
            "status": "success",
            "staff_id": staff_id,
            "latitude": latitude,
            "longitude": longitude,
            "location": location
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve staff location: {e}")
