from __future__ import annotations

import os
import math
import asyncio
from typing import Optional, Literal, List, Dict, Any, Tuple

import httpx
from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# Config
# -----------------------------
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_RADIUS_METERS = int(os.getenv("DEFAULT_RADIUS_METERS", "5000"))

GOOGLE_PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
GOOGLE_PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

Category = Literal["dental", "primary_care", "urgent_care", "optometrist", "mental_health"]

# Map your UI categories to Google Places "type" + keyword
# (Places has a limited list of types; keywords refine results)
CATEGORY_SEARCH: Dict[str, Dict[str, str]] = {
    "dental": {"type": "dentist", "keyword": "dental clinic"},
    "primary_care": {"type": "doctor", "keyword": "primary care physician"},
    "urgent_care": {"type": "hospital", "keyword": "urgent care"},
    "optometrist": {"type": "optometrist", "keyword": "optometrist"},
    "mental_health": {"type": "doctor", "keyword": "therapy psychologist counseling mental health"},
}

# -----------------------------
# Helpers
# -----------------------------
def require_key():
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_MAPS_API_KEY is not set. Put it in your .env and restart the server."
        )

def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in miles between two lat/lng points."""
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def google_maps_place_photo_url(photo_reference: str, maxwidth: int = 900) -> str:
    return (
        "https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={maxwidth}&photo_reference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
    )

# Small in-memory cache (hackathon-friendly)
_CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 60

def cache_get(key: str):
    item = _CACHE.get(key)
    if not item:
        return None
    ts, val = item
    now = asyncio.get_event_loop().time()
    if (now - ts) > CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return val

def cache_set(key: str, value: Any):
    _CACHE[key] = (asyncio.get_event_loop().time(), value)

# -----------------------------
# Models
# -----------------------------
class ProviderOut(BaseModel):
    place_id: str
    name: str
    category: Category
    address: str
    lat: float
    lng: float
    open_now: Optional[bool] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    distance_miles: float

    # Optional details (extra API calls)
    phone: Optional[str] = None
    website: Optional[str] = None

    # Optional photo
    photo_url: Optional[str] = None

class ProvidersResponse(BaseModel):
    providers: List[ProviderOut]

class HelpResponse(BaseModel):
    resources: List[Dict[str, str]]

class AnalyzeRequest(BaseModel):
    text: str

class AnalyzeResponse(BaseModel):
    providerType: Category

# -----------------------------
# App
# -----------------------------
app = FastAPI(title="CareNav Backend (Google Places)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for demo; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Help button resources
# -----------------------------
HELP_RESOURCES = [
    {
        "title": "Emergency (Life-threatening)",
        "action": "Call 911",
        "phone": "911",
        "note": "If chest pain, severe bleeding, trouble breathing, or loss of consciousness."
    },
    {
        "title": "Mental Health Crisis",
        "action": "Call/text 988",
        "phone": "988",
        "note": "Suicide & Crisis Lifeline (US)."
    },
    {
        "title": "UCSB Student Health",
        "action": "Call Student Health",
        "phone": "+1-805-893-3371",
        "note": "Appointments, advice nurse, referrals."
    },
]

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/help", response_model=HelpResponse)
def help_resources():
    return {"resources": HELP_RESOURCES}

@app.post("/api/analyze-health-need", response_model=AnalyzeResponse)
async def analyze_health_need(request: AnalyzeRequest):
    """
    Analyzes user text using OpenAI to suggest the appropriate healthcare provider type.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set. Put it in your .env file."
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a healthcare assistant helping students at UCSB determine which type of healthcare provider they need. 
                            Based on the user's description, suggest ONE of the following provider types:
                            - dental (for dental issues, tooth pain, oral health, cleanings)
                            - primary_care (for general health, check-ups, non-urgent medical issues, ongoing care)
                            - urgent_care (for immediate but non-life-threatening medical attention, injuries, sudden illness)
                            - optometrist (for eye exams, vision problems, eye care)
                            - mental_health (for mental health, therapy, counseling, emotional support, anxiety, depression)
                            
                            Respond with ONLY the provider type key (dental, primary_care, urgent_care, optometrist, or mental_health) in lowercase, nothing else."""
                        },
                        {
                            "role": "user",
                            "content": request.text
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 10
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenAI API error: {error_data.get('error', {}).get('message', 'Unknown error')}"
                )
            
            data = response.json()
            provider_type = data["choices"][0]["message"]["content"].strip().lower()
            
            # Validate provider type
            if provider_type not in ["dental", "primary_care", "urgent_care", "optometrist", "mental_health"]:
                # Default to primary_care if invalid response
                provider_type = "primary_care"
            
            return AnalyzeResponse(providerType=provider_type)
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing request: {str(e)}")

# -----------------------------
# Google Places calls
# -----------------------------
async def places_nearby_search(
    client: httpx.AsyncClient,
    *,
    lat: float,
    lng: float,
    radius_m: int,
    place_type: str,
    keyword: str,
    open_now: Optional[bool],
) -> Dict[str, Any]:
    params = {
        "key": GOOGLE_MAPS_API_KEY,
        "location": f"{lat},{lng}",
        "radius": str(radius_m),
        "type": place_type,
        "keyword": keyword,
    }
    if open_now is True:
        params["opennow"] = "true"

    r = await client.get(GOOGLE_PLACES_NEARBY_URL, params=params, timeout=20)
    data = r.json()

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise HTTPException(
            status_code=502,
            detail=f"Google Places error: {status} - {data.get('error_message','')}"
        )
    return data

async def places_details(
    client: httpx.AsyncClient,
    *,
    place_id: str,
) -> Dict[str, Any]:
    # Minimal fields to reduce quota usage
    params = {
        "key": GOOGLE_MAPS_API_KEY,
        "place_id": place_id,
        "fields": "formatted_phone_number,website",
    }
    r = await client.get(GOOGLE_PLACES_DETAILS_URL, params=params, timeout=20)
    data = r.json()
    if data.get("status") != "OK":
        return {}
    return data.get("result", {}) or {}

# -----------------------------
# Main endpoint (category-based)
# -----------------------------
@app.get("/providers", response_model=ProvidersResponse)
async def providers(
    category: Category = Query(..., description="dental | primary_care | urgent_care | optometrist | mental_health"),
    user_lat: float = Query(..., description="User latitude"),
    user_lng: float = Query(..., description="User longitude"),
    radius_meters: int = Query(DEFAULT_RADIUS_METERS, ge=500, le=50000, description="Search radius in meters"),
    open_now: Optional[bool] = Query(None, description="If true, only return places open now"),
    limit: int = Query(15, ge=1, le=25, description="Max results"),
    include_details: bool = Query(False, description="If true, fetch phone/website (more API calls)"),
):
    """
    Returns real nearby providers using Google Places.
    Your frontend decides the category (Dental, Primary care, etc).
    """
    require_key()

    search = CATEGORY_SEARCH.get(category)
    if not search:
        raise HTTPException(status_code=400, detail="Invalid category")

    # Cache key (rounded coords so cache hits more often)
    ck = f"{category}:{user_lat:.4f},{user_lng:.4f}:{radius_meters}:{open_now}:{limit}:{include_details}"
    cached = cache_get(ck)
    if cached:
        return cached

    place_type = search["type"]
    keyword = search["keyword"]

    async with httpx.AsyncClient() as client:
        data = await places_nearby_search(
            client,
            lat=user_lat,
            lng=user_lng,
            radius_m=radius_meters,
            place_type=place_type,
            keyword=keyword,
            open_now=open_now,
        )

        results = data.get("results", []) or []
        providers_out: List[ProviderOut] = []

        for item in results[:limit]:
            loc = (item.get("geometry") or {}).get("location") or {}
            plat = loc.get("lat")
            plng = loc.get("lng")
            if plat is None or plng is None:
                continue

            dist = haversine_miles(user_lat, user_lng, float(plat), float(plng))
            opening = item.get("opening_hours") or {}
            is_open = opening.get("open_now")

            photo_url = None
            photos = item.get("photos") or []
            if photos and photos[0].get("photo_reference"):
                photo_url = google_maps_place_photo_url(photos[0]["photo_reference"], maxwidth=900)

            providers_out.append(
                ProviderOut(
                    place_id=item.get("place_id", ""),
                    name=item.get("name", "Unknown"),
                    category=category,
                    address=item.get("vicinity") or item.get("formatted_address") or "Address unavailable",
                    lat=float(plat),
                    lng=float(plng),
                    open_now=is_open if isinstance(is_open, bool) else None,
                    rating=item.get("rating"),
                    user_ratings_total=item.get("user_ratings_total"),
                    distance_miles=round(dist, 2),
                    photo_url=photo_url,
                )
            )

        # Optional details (phone/website) — extra requests
        if include_details and providers_out:
            async def add_details(p: ProviderOut):
                d = await places_details(client, place_id=p.place_id)
                p.phone = d.get("formatted_phone_number")
                p.website = d.get("website")
                return p

            providers_out = list(await asyncio.gather(*[add_details(p) for p in providers_out]))

        resp = ProvidersResponse(providers=providers_out)
        cache_set(ck, resp)
        return resp
