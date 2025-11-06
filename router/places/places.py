from fastapi import APIRouter, HTTPException, Query
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/api/v1/places",
    tags=["places"]
)

@router.get("/suggest")
async def suggest_places(
    input: str = Query(..., description="User's search input (e.g., 'La')"),
    language: str = Query("en", description="Language for results, default is English")
):
    """
    Suggest locations based on user input using Google Places Autocomplete API.
    """
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise HTTPException(status_code=500, detail="Google API key not configured")

        autocomplete_url = (
            f"https://maps.googleapis.com/maps/api/place/autocomplete/json"
            f"?input={input}&language={language}&key={google_api_key}"
        )

        response = requests.get(autocomplete_url)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            return {
                "status": "error",
                "message": data.get("error_message", "No suggestions found"),
                "predictions": []
            }

        # Extract and format predictions
        suggestions = [
            {
                "description": item.get("description"),
                # "place_id": item.get("place_id")
            }
            for item in data.get("predictions", [])
        ]

        return {
            "status": "success",
            "query": input,
            "suggestions": suggestions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch place suggestions: {e}")
