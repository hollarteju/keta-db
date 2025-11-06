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

