"""
Weather Agent
=============

Analyzes seasonal and weather suitability for farming.
Uses Open-Meteo free API for live weather data with fallback to historical averages.
Does NOT recommend crops - only provides weather insights.

Enhanced Features:
- Live weather data from Open-Meteo API (free, no API key)
- Location-aware weather profiles (state/district level)
- Rainfall pattern analysis and irrigation needs
- Frost and heat stress risk assessment
- Drought and flood indicators
- Data freshness tracking with confidence scoring
- Progressive fallback (Live API → PINCODE → District → State)
- SELF-LEARNING: Automatically learns unknown pincodes via India Post API
- Stores location details (state, district, post offices) in DynamoDB
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from utils.logger import logger
from utils.learning_db import (
    get_pincode_coordinates as db_get_pincode,
    learn_pincode,
    save_weather_observation,
    learn_pincode_location,
    get_pincode_location
)


# Coordinates for major Indian cities/pincodes (lat, lon)
PINCODE_COORDINATES = {
    # Maharashtra
    "411001": (18.5204, 73.8567),  # Pune
    "400001": (19.0760, 72.8777),  # Mumbai
    "440001": (21.1458, 79.0882),  # Nagpur
    # Punjab
    "141001": (30.9010, 75.8573),  # Ludhiana
    "160001": (30.7333, 76.7794),  # Chandigarh
    "143001": (31.6340, 74.8723),  # Amritsar
    # Rajasthan
    "302001": (26.9124, 75.7873),  # Jaipur
    "342001": (26.2389, 73.0243),  # Jodhpur
    "313001": (24.5854, 73.7125),  # Udaipur
    # Odisha
    "756002": (21.4934, 86.9135),  # Balasore
    "751001": (20.2961, 85.8245),  # Bhubaneswar
    "753001": (20.4625, 85.8830),  # Cuttack
    # Karnataka
    "560001": (12.9716, 77.5946),  # Bangalore
    "580001": (15.3647, 75.1240),  # Hubli
    "570001": (12.2958, 76.6394),  # Mysore
    # Tamil Nadu
    "600001": (13.0827, 80.2707),  # Chennai
    "641001": (11.0168, 76.9558),  # Coimbatore
    "625001": (9.9252, 78.1198),   # Madurai
    # West Bengal
    "700001": (22.5726, 88.3639),  # Kolkata
    "713101": (23.5204, 87.3119),  # Durgapur
    # Uttar Pradesh
    "226001": (26.8467, 80.9462),  # Lucknow
    "208001": (26.4499, 80.3319),  # Kanpur
    "221001": (25.3176, 82.9739),  # Varanasi
    # Gujarat
    "380001": (23.0225, 72.5714),  # Ahmedabad
    "395001": (21.1702, 72.8311),  # Surat
    "390001": (22.3072, 73.1812),  # Vadodara
    # Madhya Pradesh
    "462001": (23.2599, 77.4126),  # Bhopal
    "452001": (22.7196, 75.8577),  # Indore
    # Kerala
    "695001": (8.5241, 76.9366),   # Thiruvananthapuram
    "682001": (9.9312, 76.2673),   # Kochi
}

# State center coordinates (fallback)
STATE_COORDINATES = {
    "punjab": (31.1471, 75.3412),
    "maharashtra": (19.7515, 75.7139),
    "rajasthan": (27.0238, 74.2179),
    "kerala": (10.8505, 76.2711),
    "west_bengal": (22.9868, 87.8550),
    "uttar_pradesh": (26.8467, 80.9462),
    "tamil_nadu": (11.1271, 78.6569),
    "karnataka": (15.3173, 75.7139),
    "madhya_pradesh": (22.9734, 78.6569),
    "gujarat": (22.2587, 71.1924),
    "odisha": (20.9517, 85.0985),
    "bihar": (25.0961, 85.3131),
    "andhra_pradesh": (15.9129, 79.7400),
    "telangana": (18.1124, 79.0193),
    "haryana": (29.0588, 76.0856),
    "default": (20.5937, 78.9629),  # Center of India
}


def _fetch_live_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Fetch live weather data from Open-Meteo API (free, no API key needed).
    
    Returns current weather and 7-day forecast.
    """
    try:
        # Open-Meteo API URL
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation,weather_code"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"
            f"&timezone=Asia/Kolkata"
            f"&forecast_days=7"
        )
        
        logger.info(f"Fetching weather from Open-Meteo: lat={lat}, lon={lon}")
        
        req = urllib.request.Request(url, headers={'User-Agent': 'FarmerAssistant/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        
        # Parse response
        current = data.get("current", {})
        daily = data.get("daily", {})
        
        # Calculate averages from forecast
        temp_mins = daily.get("temperature_2m_min", [])
        temp_maxs = daily.get("temperature_2m_max", [])
        precip_sums = daily.get("precipitation_sum", [])
        
        avg_temp_min = sum(temp_mins) / len(temp_mins) if temp_mins else 20
        avg_temp_max = sum(temp_maxs) / len(temp_maxs) if temp_maxs else 30
        total_rainfall = sum(precip_sums) if precip_sums else 0
        
        # Estimate monthly rainfall from weekly forecast
        estimated_monthly_rainfall = total_rainfall * 4  # Rough estimate
        
        weather_result = {
            "current_temp": current.get("temperature_2m", 25),
            "current_humidity": current.get("relative_humidity_2m", 60),
            "current_precipitation": current.get("precipitation", 0),
            "temp_min": round(avg_temp_min, 1),
            "temp_max": round(avg_temp_max, 1),
            "rainfall": round(estimated_monthly_rainfall, 1),
            "humidity": current.get("relative_humidity_2m", 60),
            "forecast_days": len(temp_mins),
            "weather_code": current.get("weather_code", 0),
            "data_source": "open_meteo_live",
            "fetched_at": datetime.now().isoformat()
        }
        
        logger.info(f"Live weather fetched: temp={weather_result['temp_min']}-{weather_result['temp_max']}°C, rainfall={weather_result['rainfall']}mm")
        return weather_result
        
    except urllib.error.URLError as e:
        logger.warning(f"Weather API network error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Weather API error: {e}")
        return None


def _get_coordinates(context: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], str]:
    """
    Get coordinates from pincode or state.
    Uses self-learning: unknown pincodes are looked up via India Post API and stored.
    
    Returns: (latitude, longitude, source)
    """
    pincode = context.get("pincode")
    state = (context.get("state") or "").lower().replace(" ", "_")
    
    # Try pincode first from static mapping
    if pincode and pincode in PINCODE_COORDINATES:
        lat, lon = PINCODE_COORDINATES[pincode]
        return lat, lon, f"pincode_{pincode}"
    
    # Try pincode from learning database
    if pincode:
        db_coords = db_get_pincode(pincode)
        if db_coords:
            lat, lon = db_coords
            logger.info(f"Found pincode {pincode} in learning DB")
            return lat, lon, f"learned_pincode_{pincode}"
        
        # Self-learn: fetch from India Post API and geocode
        logger.info(f"Learning new pincode via India Post API: {pincode}")
        location_data = learn_pincode_location(pincode)
        if location_data:
            # Update context with learned location info
            if location_data.get('state') and not context.get('state'):
                context['state'] = location_data['state']
            if location_data.get('district') and not context.get('district'):
                context['district'] = location_data['district']
            
            # Get coordinates if available
            if location_data.get('latitude') and location_data.get('longitude'):
                lat, lon = location_data['latitude'], location_data['longitude']
                logger.info(f"Learned pincode {pincode}: {location_data.get('district')}, {location_data.get('state')}")
                return lat, lon, f"india_post_pincode_{pincode}"
            
            # Fallback to state coordinates using the learned state
            learned_state = location_data.get('state', '').lower().replace(" ", "_")
            if learned_state in STATE_COORDINATES:
                lat, lon = STATE_COORDINATES[learned_state]
                logger.info(f"Using state coords for learned pincode {pincode}: {learned_state}")
                return lat, lon, f"india_post_state_{learned_state}"
        
        # Last resort: try basic geocoding
        learned_coords = learn_pincode(pincode)
        if learned_coords:
            lat, lon = learned_coords
            logger.info(f"Geocoded pincode {pincode}: {lat}, {lon}")
            return lat, lon, f"geocoded_pincode_{pincode}"
    
    # Try state
    if state and state in STATE_COORDINATES:
        lat, lon = STATE_COORDINATES[state]
        return lat, lon, f"state_{state}"
    
    # Default to center of India
    lat, lon = STATE_COORDINATES["default"]
    return lat, lon, "default_india"


def enrich_context_from_pincode(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich context with location details from pincode.
    Uses India Post API to get state, district, and other location info.
    
    Args:
        context: Context dict with optional pincode
        
    Returns:
        Enriched context with state, district, etc.
    """
    pincode = context.get("pincode")
    if not pincode:
        return context
    
    # Check if we already have complete location info
    if context.get("state") and context.get("district"):
        return context
    
    # Try to get location from learning DB or API
    location = get_pincode_location(pincode)
    if not location:
        location = learn_pincode_location(pincode)
    
    if location:
        # Enrich context with learned location data
        if not context.get("state"):
            context["state"] = location.get("state", "")
        if not context.get("district"):
            context["district"] = location.get("district", "")
        if location.get("primary_location"):
            context["locality"] = location.get("primary_location", "")
        context["location_source"] = "india_post_api"
        logger.info(f"Enriched context from pincode {pincode}: {context.get('district')}, {context.get('state')}")
    
    return context


# Regional weather profiles for Indian states (historical averages)
REGIONAL_WEATHER_PROFILES = {
    "punjab": {
        "kharif": {"temp_min": 25, "temp_max": 38, "rainfall": 650, "humidity": 70, "frost_risk": "none"},
        "rabi": {"temp_min": 5, "temp_max": 22, "rainfall": 80, "humidity": 55, "frost_risk": "moderate"},
        "zaid": {"temp_min": 22, "temp_max": 42, "rainfall": 50, "humidity": 45, "frost_risk": "none"}
    },
    "maharashtra": {
        "kharif": {"temp_min": 22, "temp_max": 32, "rainfall": 1200, "humidity": 80, "frost_risk": "none"},
        "rabi": {"temp_min": 12, "temp_max": 28, "rainfall": 50, "humidity": 45, "frost_risk": "low"},
        "zaid": {"temp_min": 20, "temp_max": 38, "rainfall": 100, "humidity": 50, "frost_risk": "none"}
    },
    "rajasthan": {
        "kharif": {"temp_min": 26, "temp_max": 40, "rainfall": 350, "humidity": 55, "frost_risk": "none"},
        "rabi": {"temp_min": 8, "temp_max": 25, "rainfall": 20, "humidity": 35, "frost_risk": "moderate"},
        "zaid": {"temp_min": 25, "temp_max": 45, "rainfall": 30, "humidity": 30, "frost_risk": "none"}
    },
    "kerala": {
        "kharif": {"temp_min": 23, "temp_max": 30, "rainfall": 2500, "humidity": 90, "frost_risk": "none"},
        "rabi": {"temp_min": 22, "temp_max": 32, "rainfall": 200, "humidity": 65, "frost_risk": "none"},
        "zaid": {"temp_min": 25, "temp_max": 35, "rainfall": 400, "humidity": 75, "frost_risk": "none"}
    },
    "west_bengal": {
        "kharif": {"temp_min": 24, "temp_max": 34, "rainfall": 1400, "humidity": 85, "frost_risk": "none"},
        "rabi": {"temp_min": 10, "temp_max": 25, "rainfall": 50, "humidity": 50, "frost_risk": "low"},
        "zaid": {"temp_min": 22, "temp_max": 38, "rainfall": 200, "humidity": 70, "frost_risk": "none"}
    },
    "uttar_pradesh": {
        "kharif": {"temp_min": 25, "temp_max": 36, "rainfall": 900, "humidity": 75, "frost_risk": "none"},
        "rabi": {"temp_min": 6, "temp_max": 22, "rainfall": 60, "humidity": 50, "frost_risk": "moderate"},
        "zaid": {"temp_min": 22, "temp_max": 42, "rainfall": 80, "humidity": 45, "frost_risk": "none"}
    },
    "tamil_nadu": {
        "kharif": {"temp_min": 24, "temp_max": 35, "rainfall": 400, "humidity": 70, "frost_risk": "none"},
        "rabi": {"temp_min": 20, "temp_max": 30, "rainfall": 600, "humidity": 75, "frost_risk": "none"},
        "zaid": {"temp_min": 26, "temp_max": 38, "rainfall": 100, "humidity": 60, "frost_risk": "none"}
    },
    "karnataka": {
        "kharif": {"temp_min": 20, "temp_max": 30, "rainfall": 900, "humidity": 80, "frost_risk": "none"},
        "rabi": {"temp_min": 15, "temp_max": 28, "rainfall": 100, "humidity": 50, "frost_risk": "low"},
        "zaid": {"temp_min": 22, "temp_max": 36, "rainfall": 150, "humidity": 55, "frost_risk": "none"}
    },
    "madhya_pradesh": {
        "kharif": {"temp_min": 24, "temp_max": 35, "rainfall": 1100, "humidity": 75, "frost_risk": "none"},
        "rabi": {"temp_min": 8, "temp_max": 26, "rainfall": 40, "humidity": 45, "frost_risk": "moderate"},
        "zaid": {"temp_min": 24, "temp_max": 42, "rainfall": 60, "humidity": 40, "frost_risk": "none"}
    },
    "gujarat": {
        "kharif": {"temp_min": 25, "temp_max": 35, "rainfall": 700, "humidity": 75, "frost_risk": "none"},
        "rabi": {"temp_min": 12, "temp_max": 28, "rainfall": 30, "humidity": 40, "frost_risk": "low"},
        "zaid": {"temp_min": 26, "temp_max": 42, "rainfall": 50, "humidity": 45, "frost_risk": "none"}
    },
    "default": {
        "kharif": {"temp_min": 22, "temp_max": 35, "rainfall": 800, "humidity": 75, "frost_risk": "none"},
        "rabi": {"temp_min": 10, "temp_max": 25, "rainfall": 50, "humidity": 45, "frost_risk": "low"},
        "zaid": {"temp_min": 25, "temp_max": 40, "rainfall": 200, "humidity": 55, "frost_risk": "none"}
    }
}

# Crop-weather suitability database
CROP_WEATHER_REQUIREMENTS = {
    "rice": {"temp_min": 20, "temp_max": 35, "rainfall_min": 1000, "humidity_min": 70, "frost_tolerant": False},
    "wheat": {"temp_min": 10, "temp_max": 25, "rainfall_min": 50, "humidity_min": 40, "frost_tolerant": True},
    "maize": {"temp_min": 18, "temp_max": 32, "rainfall_min": 500, "humidity_min": 50, "frost_tolerant": False},
    "cotton": {"temp_min": 20, "temp_max": 35, "rainfall_min": 600, "humidity_min": 60, "frost_tolerant": False},
    "sugarcane": {"temp_min": 20, "temp_max": 35, "rainfall_min": 1200, "humidity_min": 70, "frost_tolerant": False},
    "soybean": {"temp_min": 18, "temp_max": 30, "rainfall_min": 500, "humidity_min": 60, "frost_tolerant": False},
    "groundnut": {"temp_min": 20, "temp_max": 32, "rainfall_min": 400, "humidity_min": 50, "frost_tolerant": False},
    "chickpea": {"temp_min": 10, "temp_max": 25, "rainfall_min": 40, "humidity_min": 35, "frost_tolerant": True},
    "mustard": {"temp_min": 10, "temp_max": 25, "rainfall_min": 30, "humidity_min": 40, "frost_tolerant": True},
    "barley": {"temp_min": 8, "temp_max": 22, "rainfall_min": 40, "humidity_min": 35, "frost_tolerant": True},
    "millet": {"temp_min": 20, "temp_max": 38, "rainfall_min": 300, "humidity_min": 40, "frost_tolerant": False},
    "sorghum": {"temp_min": 20, "temp_max": 38, "rainfall_min": 350, "humidity_min": 45, "frost_tolerant": False},
    "potato": {"temp_min": 15, "temp_max": 25, "rainfall_min": 100, "humidity_min": 60, "frost_tolerant": False},
    "onion": {"temp_min": 15, "temp_max": 30, "rainfall_min": 50, "humidity_min": 50, "frost_tolerant": False}
}


def analyze_weather(query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Analyze weather suitability from user query.

    Args:
        query: User's text query (e.g., "planning for kharif season")
        context: Optional location/context data including:
            - pincode: User's location pincode
            - district: District name
            - state: State name
            - target_date: Specific date for analysis

    Returns:
        Structured JSON response with weather analysis including:
        - Season and weather parameters
        - Risk assessments (frost, drought, flood)
        - Weather-suitable crops (not recommendations)
        - Data source and confidence tracking
    """
    # Ensure query is never None
    query = query or ""
    context = context or {}
    
    try:
        logger.info(f"Weather Agent analyzing: {query}")

        # Extract season and location from query
        season_data = _extract_season_info(query, context)
        location_data = _get_location_context(context)
        
        # Try to get live weather data first
        live_weather = None
        lat, lon, coord_source = _get_coordinates(context)
        if lat and lon:
            live_weather = _fetch_live_weather(lat, lon)
        
        # Get weather data with location awareness (uses live data if available)
        weather_data = _get_weather_data(season_data, location_data, live_weather, coord_source)

        # Calculate suitability score with confidence
        suitability_score, suitability_confidence = _calculate_suitability(weather_data)
        
        # Assess various risks
        risk_assessment = _assess_comprehensive_risks(weather_data)
        
        # Get weather-suitable crops
        optimal_crops = _suggest_weather_suitable_crops(weather_data)
        
        # Calculate irrigation needs
        irrigation_needs = _calculate_irrigation_needs(weather_data)

        response = {
            "season": season_data.get("season", "unknown"),
            "season_dates": _get_season_dates(season_data.get("season", "kharif")),
            "temperature_range": {
                "min": weather_data.get("temp_min", 20.0),
                "max": weather_data.get("temp_max", 30.0),
                "optimal_range": weather_data.get("optimal_temp_range", "20-30°C")
            },
            "rainfall_mm": weather_data.get("rainfall", 100.0),
            "rainfall_pattern": weather_data.get("rainfall_pattern", "normal"),
            "humidity_percent": weather_data.get("humidity", 60.0),
            "suitability_score": suitability_score,
            "suitability_confidence": suitability_confidence,
            "risk_assessment": risk_assessment,
            "risk_factors": risk_assessment.get("summary", []),
            "irrigation_needs": irrigation_needs,
            "optimal_crops": optimal_crops,
            "data_sources": weather_data.get("data_sources", ["historical_average"]),
            "data_freshness": weather_data.get("data_freshness", "historical"),
            "location_context": {
                "pincode": context.get("pincode"),
                "district": context.get("district"),
                "state": context.get("state"),
                "fallback_level": location_data.get("fallback_level", "default")
            }
        }

        # Self-learning: Save weather observation if we got live data
        if live_weather and context.get("state"):
            try:
                save_weather_observation(
                    region=context.get("state"),
                    season=season_data.get("season", "unknown"),
                    temp_min=weather_data.get("temp_min", 20),
                    temp_max=weather_data.get("temp_max", 30),
                    rainfall=weather_data.get("rainfall", 0),
                    humidity=weather_data.get("humidity", 60),
                    source="open_meteo_live"
                )
            except Exception as obs_err:
                logger.debug(f"Could not save weather observation: {obs_err}")

        logger.info(f"Weather Agent response: suitability={suitability_score}, confidence={suitability_confidence}")
        return response

    except Exception as e:
        logger.error(f"Weather Agent error: {e}")
        return {
            "error": str(e),
            "season": "unknown",
            "season_dates": {},
            "temperature_range": {"min": 20.0, "max": 30.0, "optimal_range": "20-30°C"},
            "rainfall_mm": 100.0,
            "rainfall_pattern": "unknown",
            "humidity_percent": 60.0,
            "suitability_score": 5,
            "suitability_confidence": 0.1,
            "risk_assessment": {"summary": ["Analysis failed"]},
            "risk_factors": ["Analysis failed - using defaults"],
            "irrigation_needs": {"level": "moderate", "frequency": "weekly"},
            "optimal_crops": [],
            "data_sources": ["error_fallback"],
            "data_freshness": "unknown",
            "location_context": {"fallback_level": "error"}
        }


def _get_location_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get location context for weather profile selection.
    
    Fallback order: PINCODE → District → State → Default
    """
    location_data = {
        "fallback_level": "default",
        "confidence": 0.3,
        "region": "default"
    }
    
    # Try state-level data
    state = (context.get("state") or "").lower().replace(" ", "_")
    if state in REGIONAL_WEATHER_PROFILES:
        location_data["region"] = state
        location_data["fallback_level"] = "state"
        location_data["confidence"] = 0.6
    
    # District would give higher confidence (0.75)
    # PINCODE would give highest confidence (0.9) + potentially live data
    
    return location_data


def _get_season_dates(season: str) -> Dict[str, str]:
    """Get typical dates for each season."""
    season_dates = {
        "kharif": {"start": "June 15", "end": "October 15", "sowing_window": "June-July"},
        "rabi": {"start": "November 1", "end": "March 31", "sowing_window": "October-November"},
        "zaid": {"start": "March 15", "end": "June 15", "sowing_window": "March-April"}
    }
    return season_dates.get(season, season_dates["kharif"])


def _extract_season_info(query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Extract season information from query and context."""
    query_lower = (query or "").lower()
    context = context or {}

    seasons = {
        "kharif": ["kharif", "monsoon", "rainy season", "june", "july", "august", "september"],
        "rabi": ["rabi", "winter", "cold season", "november", "december", "january", "february"],
        "zaid": ["zaid", "summer", "hot season", "march", "april", "may"]
    }

    season = None
    
    # Check query for season indicators
    for s, keywords in seasons.items():
        if any(kw in query_lower for kw in keywords):
            season = s
            break
    
    # If not in query, try to determine from current date
    if not season:
        current_month = datetime.now().month
        if current_month in [6, 7, 8, 9, 10]:
            season = "kharif"
        elif current_month in [11, 12, 1, 2, 3]:
            season = "rabi"
        else:
            season = "zaid"

    # Extract location hints from query
    location = context.get("district") or context.get("state") or "default"

    return {
        "season": season, 
        "location": location,
        "source": "query" if any(kw in query_lower for s, kws in seasons.items() for kw in kws) else "date_inferred"
    }


def _get_weather_data(
    season_data: Dict[str, Any], 
    location_data: Dict[str, Any],
    live_weather: Optional[Dict[str, Any]] = None,
    coord_source: str = "default"
) -> Dict[str, Any]:
    """Get weather data for season with location awareness and live API support."""
    season = season_data.get("season", "kharif")
    region = location_data.get("region", "default")
    
    # Get regional profile as fallback
    regional_profile = REGIONAL_WEATHER_PROFILES.get(region, REGIONAL_WEATHER_PROFILES["default"])
    season_profile = regional_profile.get(season, regional_profile.get("kharif", {}))
    
    # Use live weather data if available, else use historical
    if live_weather:
        weather_data = {
            "temp_min": live_weather.get("temp_min", season_profile.get("temp_min", 22)),
            "temp_max": live_weather.get("temp_max", season_profile.get("temp_max", 35)),
            "rainfall": live_weather.get("rainfall", season_profile.get("rainfall", 800)),
            "humidity": live_weather.get("humidity", season_profile.get("humidity", 75)),
            "frost_risk": "low" if live_weather.get("temp_min", 20) < 5 else "none",
            "season": season,
            "region": region,
            "current_temp": live_weather.get("current_temp"),
            "current_humidity": live_weather.get("current_humidity"),
            "forecast_days": live_weather.get("forecast_days", 7),
            "data_sources": ["open_meteo_live", coord_source, f"{region}_profile"],
            "data_freshness": "live",
            "fetched_at": live_weather.get("fetched_at")
        }
        logger.info(f"Using LIVE weather data from {coord_source}")
    else:
        weather_data = {
            "temp_min": season_profile.get("temp_min", 22),
            "temp_max": season_profile.get("temp_max", 35),
            "rainfall": season_profile.get("rainfall", 800),
            "humidity": season_profile.get("humidity", 75),
            "frost_risk": season_profile.get("frost_risk", "none"),
            "season": season,
            "region": region,
            "data_sources": ["historical_average", f"{region}_profile"],
            "data_freshness": "historical"
        }
        logger.info(f"Using HISTORICAL weather data for {region}")
    
    # Calculate derived values
    weather_data["optimal_temp_range"] = f"{weather_data['temp_min']+2}-{weather_data['temp_max']-5}°C"
    
    # Determine rainfall pattern
    rainfall = weather_data["rainfall"]
    if rainfall > 1500:
        weather_data["rainfall_pattern"] = "very_heavy"
    elif rainfall > 800:
        weather_data["rainfall_pattern"] = "heavy"
    elif rainfall > 400:
        weather_data["rainfall_pattern"] = "moderate"
    elif rainfall > 100:
        weather_data["rainfall_pattern"] = "light"
    else:
        weather_data["rainfall_pattern"] = "scanty"
    
    return weather_data


def _calculate_suitability(weather_data: Dict) -> Tuple[int, float]:
    """
    Calculate weather suitability score 1-10 with confidence.
    
    Returns:
        Tuple of (suitability_score, confidence)
    """
    score = 7  # Base score for farming
    confidence_factors = []

    # Temperature factor (optimal 20-30°C for most crops)
    temp_min = weather_data.get("temp_min", 20)
    temp_max = weather_data.get("temp_max", 30)

    if 18 <= temp_min and temp_max <= 35:
        score += 2
        confidence_factors.append(0.85)
    elif 15 <= temp_min and temp_max <= 38:
        score += 1
        confidence_factors.append(0.7)
    elif temp_min < 10 or temp_max > 42:
        score -= 3
        confidence_factors.append(0.8)
    else:
        confidence_factors.append(0.6)

    # Rainfall factor
    rainfall = weather_data.get("rainfall", 100)
    season = weather_data.get("season", "kharif")
    
    if season == "kharif":
        if 600 <= rainfall <= 1200:
            score += 1
            confidence_factors.append(0.8)
        elif rainfall > 2000:
            score -= 2  # Flooding risk
            confidence_factors.append(0.75)
        elif rainfall < 400:
            score -= 1  # Drought risk
            confidence_factors.append(0.7)
    elif season == "rabi":
        if 30 <= rainfall <= 150:
            score += 1
            confidence_factors.append(0.8)
        elif rainfall > 300:
            score -= 1  # Too wet for rabi
            confidence_factors.append(0.7)
    
    # Humidity factor
    humidity = weather_data.get("humidity", 60)
    if 50 <= humidity <= 75:
        score += 1
        confidence_factors.append(0.75)
    elif humidity > 85:
        score -= 1  # Disease pressure
        confidence_factors.append(0.7)
    
    # Frost risk factor
    frost_risk = weather_data.get("frost_risk", "none")
    if frost_risk == "high":
        score -= 2
        confidence_factors.append(0.8)
    elif frost_risk == "moderate":
        score -= 1
        confidence_factors.append(0.75)
    
    confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    return max(1, min(10, score)), round(confidence, 2)


def _assess_comprehensive_risks(weather_data: Dict) -> Dict[str, Any]:
    """Assess comprehensive weather-related risks."""
    risks = {
        "frost": {"level": "none", "details": ""},
        "drought": {"level": "none", "details": ""},
        "flood": {"level": "none", "details": ""},
        "heat_stress": {"level": "none", "details": ""},
        "disease_pressure": {"level": "none", "details": ""},
        "summary": []
    }
    
    temp_max = weather_data.get("temp_max", 30)
    temp_min = weather_data.get("temp_min", 20)
    rainfall = weather_data.get("rainfall", 100)
    humidity = weather_data.get("humidity", 60)
    frost_risk = weather_data.get("frost_risk", "none")
    
    # Frost risk
    if frost_risk == "high" or temp_min < 5:
        risks["frost"] = {"level": "high", "details": "Significant frost damage risk for sensitive crops"}
        risks["summary"].append("[HIGH] Frost risk - protect sensitive crops with covers")
    elif frost_risk == "moderate" or temp_min < 10:
        risks["frost"] = {"level": "moderate", "details": "Possible frost in early morning"}
        risks["summary"].append("[MODERATE] Frost possible - avoid frost-sensitive varieties")
    
    # Heat stress
    if temp_max > 42:
        risks["heat_stress"] = {"level": "high", "details": "Severe heat stress likely"}
        risks["summary"].append("[HIGH] Heat stress - ensure irrigation, consider shade nets")
    elif temp_max > 38:
        risks["heat_stress"] = {"level": "moderate", "details": "Heat stress possible during peak hours"}
        risks["summary"].append("[MODERATE] Heat stress risk - water crops during cooler hours")
    
    # Drought risk
    season = weather_data.get("season", "kharif")
    if season == "kharif" and rainfall < 400:
        risks["drought"] = {"level": "high", "details": "Insufficient monsoon rainfall expected"}
        risks["summary"].append("[HIGH] Drought risk - plan irrigation backup")
    elif rainfall < 200:
        risks["drought"] = {"level": "moderate", "details": "Below average rainfall expected"}
        risks["summary"].append("[MODERATE] Low rainfall - schedule regular irrigation")
    
    # Flood risk
    if rainfall > 2000:
        risks["flood"] = {"level": "high", "details": "Very heavy rainfall may cause flooding"}
        risks["summary"].append("[HIGH] Flooding risk - ensure field drainage")
    elif rainfall > 1500:
        risks["flood"] = {"level": "moderate", "details": "Heavy rainfall may cause waterlogging"}
        risks["summary"].append("[MODERATE] Waterlogging possible - improve drainage")
    
    # Disease pressure
    if humidity > 85:
        risks["disease_pressure"] = {"level": "high", "details": "High humidity favors fungal diseases"}
        risks["summary"].append("[HIGH] Disease risk - plan preventive sprays")
    elif humidity > 75:
        risks["disease_pressure"] = {"level": "moderate", "details": "Moderate disease pressure expected"}
        risks["summary"].append("[MODERATE] Disease pressure - monitor crops regularly")
    
    if not risks["summary"]:
        risks["summary"].append("No major weather risks identified for this period")
    
    return risks


def _calculate_irrigation_needs(weather_data: Dict) -> Dict[str, Any]:
    """Calculate irrigation requirements based on weather."""
    rainfall = weather_data.get("rainfall", 100)
    temp_max = weather_data.get("temp_max", 30)
    humidity = weather_data.get("humidity", 60)
    season = weather_data.get("season", "kharif")
    
    # Base evapotranspiration estimation (simplified)
    et_factor = (temp_max - 20) * 0.15 + (100 - humidity) * 0.05
    
    # Irrigation needs calculation
    if season == "kharif" and rainfall > 800:
        irrigation = {
            "level": "minimal",
            "frequency": "only_if_dry_spell",
            "estimated_mm_per_week": 0,
            "notes": "Monsoon rainfall should be sufficient"
        }
    elif rainfall < 100:
        irrigation = {
            "level": "critical",
            "frequency": "every_2_3_days",
            "estimated_mm_per_week": 50 + int(et_factor * 10),
            "notes": "Very low rainfall - regular irrigation essential"
        }
    elif rainfall < 400:
        irrigation = {
            "level": "high",
            "frequency": "twice_weekly",
            "estimated_mm_per_week": 35 + int(et_factor * 5),
            "notes": "Supplemental irrigation needed"
        }
    elif rainfall < 800:
        irrigation = {
            "level": "moderate",
            "frequency": "weekly",
            "estimated_mm_per_week": 20 + int(et_factor * 3),
            "notes": "Irrigation during dry spells"
        }
    else:
        irrigation = {
            "level": "low",
            "frequency": "as_needed",
            "estimated_mm_per_week": 10,
            "notes": "Rainfall likely sufficient with occasional supplementation"
        }
    
    return irrigation


def _suggest_weather_suitable_crops(weather_data: Dict) -> List[Dict[str, Any]]:
    """
    Suggest crops suitable for weather conditions with suitability scores.
    
    Returns list of crops with their weather suitability, not recommendations.
    """
    temp_max = weather_data.get("temp_max", 30)
    temp_min = weather_data.get("temp_min", 20)
    rainfall = weather_data.get("rainfall", 100)
    humidity = weather_data.get("humidity", 60)
    frost_risk = weather_data.get("frost_risk", "none")

    suitable_crops = []
    
    for crop, requirements in CROP_WEATHER_REQUIREMENTS.items():
        suitability_score = 1.0
        reasons = []
        
        # Temperature check
        if temp_min >= requirements["temp_min"] and temp_max <= requirements["temp_max"]:
            suitability_score *= 1.0
            reasons.append("temperature optimal")
        elif temp_min >= requirements["temp_min"] - 5 and temp_max <= requirements["temp_max"] + 5:
            suitability_score *= 0.7
            reasons.append("temperature marginal")
        else:
            suitability_score *= 0.3
            reasons.append("temperature unsuitable")
        
        # Rainfall check
        if rainfall >= requirements["rainfall_min"]:
            suitability_score *= 1.0
            reasons.append("rainfall sufficient")
        elif rainfall >= requirements["rainfall_min"] * 0.6:
            suitability_score *= 0.7
            reasons.append("rainfall marginal - irrigation needed")
        else:
            suitability_score *= 0.4
            reasons.append("rainfall insufficient")
        
        # Humidity check
        if humidity >= requirements["humidity_min"]:
            suitability_score *= 1.0
        else:
            suitability_score *= 0.8
        
        # Frost tolerance
        if frost_risk in ["moderate", "high"] and not requirements["frost_tolerant"]:
            suitability_score *= 0.3
            reasons.append("frost sensitive")
        elif frost_risk in ["moderate", "high"] and requirements["frost_tolerant"]:
            reasons.append("frost tolerant")
        
        if suitability_score >= 0.5:
            suitable_crops.append({
                "crop": crop,
                "weather_suitability": round(suitability_score, 2),
                "factors": reasons[:3]  # Top 3 factors
            })
    
    # Sort by suitability and return top crops
    suitable_crops.sort(key=lambda x: x["weather_suitability"], reverse=True)
    return suitable_crops[:8]