"""
Learning Database Module
========================

Provides DynamoDB-based persistent storage for learned data:
- Pincode location details (from India Post API)
- Pincode coordinates (geocoded from unknown pincodes)
- Regional soil profiles (learned from queries)
- Location-specific weather patterns

Uses:
- India Post API (api.postalpincode.in) for pincode details
- Nominatim (OpenStreetMap) for free geocoding
"""

import os
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import time

# Try to import boto3, fallback gracefully for local testing
try:
    import boto3
    from botocore.exceptions import ClientError
    DYNAMODB_AVAILABLE = True
except ImportError:
    DYNAMODB_AVAILABLE = False
    ClientError = Exception

from utils.logger import logger

# Table name from environment
TABLE_NAME = os.environ.get('LEARNING_TABLE', 'farmer-learning-db')

# Cache for DynamoDB client
_dynamodb_client = None


def _get_dynamodb():
    """Get or create DynamoDB client."""
    global _dynamodb_client
    if not DYNAMODB_AVAILABLE:
        return None
    if _dynamodb_client is None:
        _dynamodb_client = boto3.resource('dynamodb')
    return _dynamodb_client


def _get_table():
    """Get DynamoDB table."""
    dynamodb = _get_dynamodb()
    if dynamodb is None:
        return None
    try:
        return dynamodb.Table(TABLE_NAME)
    except Exception as e:
        logger.warning(f"Could not get DynamoDB table: {e}")
        return None


# ==================== PINCODE/LOCATION LEARNING ====================

def get_pincode_coordinates(pincode: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a pincode from DynamoDB.
    
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    table = _get_table()
    if table is None:
        return None
    
    try:
        response = table.get_item(
            Key={
                'pk': f'PINCODE#{pincode}',
                'sk': 'COORDS'
            }
        )
        item = response.get('Item')
        if item:
            return (float(item['latitude']), float(item['longitude']))
        return None
    except Exception as e:
        logger.warning(f"Error getting pincode from DB: {e}")
        return None


def save_pincode_coordinates(
    pincode: str, 
    latitude: float, 
    longitude: float,
    source: str = "geocoded",
    location_name: str = None
) -> bool:
    """
    Save pincode coordinates to DynamoDB.
    
    Args:
        pincode: Indian postal code
        latitude: Latitude
        longitude: Longitude
        source: How coordinates were obtained (geocoded, manual, etc.)
        location_name: Human-readable location name
    
    Returns:
        True if saved successfully
    """
    table = _get_table()
    if table is None:
        return False
    
    try:
        # Set TTL to 1 year for geocoded data
        ttl = int((datetime.now() + timedelta(days=365)).timestamp())
        
        table.put_item(
            Item={
                'pk': f'PINCODE#{pincode}',
                'sk': 'COORDS',
                'pincode': pincode,
                'latitude': str(latitude),
                'longitude': str(longitude),
                'source': source,
                'location_name': location_name or '',
                'created_at': datetime.now().isoformat(),
                'ttl': ttl
            }
        )
        logger.info(f"Saved pincode {pincode} coordinates to DB: {latitude}, {longitude}")
        return True
    except Exception as e:
        logger.error(f"Error saving pincode to DB: {e}")
        return False


def geocode_indian_pincode(pincode: str) -> Optional[Dict[str, Any]]:
    """
    Geocode an Indian pincode using Nominatim (OpenStreetMap).
    Free API, no key required, but has rate limits (1 req/sec).
    
    Returns:
        Dict with lat, lon, display_name or None if not found
    """
    try:
        # Nominatim API for geocoding
        query = urllib.parse.quote(f"{pincode}, India")
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1&countrycodes=in"
        
        # Add user agent (required by Nominatim)
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'FarmerAssistant/1.0 (Agricultural Advisory App)'}
        )
        
        # Rate limit: wait 1 second between requests
        time.sleep(1)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        if data and len(data) > 0:
            result = data[0]
            return {
                'latitude': float(result['lat']),
                'longitude': float(result['lon']),
                'display_name': result.get('display_name', ''),
                'source': 'nominatim_geocoded'
            }
        
        logger.warning(f"Pincode {pincode} not found in geocoding")
        return None
        
    except urllib.error.URLError as e:
        logger.warning(f"Geocoding network error for {pincode}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Geocoding error for {pincode}: {e}")
        return None


def fetch_pincode_details(pincode: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed pincode information from India Post API.
    API: https://api.postalpincode.in/pincode/{pincode}
    
    Returns location details including:
    - State
    - District
    - Division
    - Post offices with their details
    - Region/Circle info
    
    Returns:
        Dict with location details or None if not found
    """
    try:
        url = f"https://api.postalpincode.in/pincode/{pincode}"
        
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'FarmerAssistant/1.0'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        # API returns a list with one item
        if not data or len(data) == 0:
            logger.warning(f"Empty response for pincode {pincode}")
            return None
        
        result = data[0]
        
        # Check status
        if result.get('Status') != 'Success':
            logger.warning(f"Pincode {pincode} not found: {result.get('Message')}")
            return None
        
        post_offices = result.get('PostOffice', [])
        if not post_offices:
            logger.warning(f"No post offices found for pincode {pincode}")
            return None
        
        # Get primary post office (first one) for main details
        primary_po = post_offices[0]
        
        # Build location details
        location_details = {
            'pincode': pincode,
            'state': primary_po.get('State', ''),
            'district': primary_po.get('District', ''),
            'division': primary_po.get('Division', ''),
            'region': primary_po.get('Region', ''),
            'circle': primary_po.get('Circle', ''),
            'block': primary_po.get('Block', ''),
            'branch_type': primary_po.get('BranchType', ''),
            'delivery_status': primary_po.get('DeliveryStatus', ''),
            'post_offices': [
                {
                    'name': po.get('Name', ''),
                    'branch_type': po.get('BranchType', ''),
                    'delivery_status': po.get('DeliveryStatus', ''),
                    'block': po.get('Block', '')
                }
                for po in post_offices
            ],
            'primary_location': primary_po.get('Name', ''),
            'source': 'india_post_api'
        }
        
        logger.info(f"Fetched pincode {pincode}: {location_details['district']}, {location_details['state']}")
        return location_details
        
    except urllib.error.URLError as e:
        logger.warning(f"India Post API network error for {pincode}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"India Post API JSON error for {pincode}: {e}")
        return None
    except Exception as e:
        logger.warning(f"India Post API error for {pincode}: {e}")
        return None


def get_pincode_location(pincode: str) -> Optional[Dict[str, Any]]:
    """
    Get full location details for a pincode from DynamoDB.
    
    Returns:
        Dict with state, district, coordinates, etc. or None if not found
    """
    table = _get_table()
    if table is None:
        return None
    
    try:
        response = table.get_item(
            Key={
                'pk': f'PINCODE#{pincode}',
                'sk': 'LOCATION'
            }
        )
        item = response.get('Item')
        if item and 'location_data' in item:
            return json.loads(item['location_data'])
        return None
    except Exception as e:
        logger.warning(f"Error getting pincode location from DB: {e}")
        return None


def save_pincode_location(pincode: str, location_data: Dict[str, Any]) -> bool:
    """
    Save full pincode location details to DynamoDB.
    
    Args:
        pincode: Indian postal code
        location_data: Dict containing state, district, post offices, etc.
    
    Returns:
        True if saved successfully
    """
    table = _get_table()
    if table is None:
        return False
    
    try:
        # Set TTL to 2 years (location data is fairly stable)
        ttl = int((datetime.now() + timedelta(days=730)).timestamp())
        
        table.put_item(
            Item={
                'pk': f'PINCODE#{pincode}',
                'sk': 'LOCATION',
                'pincode': pincode,
                'state': location_data.get('state', ''),
                'district': location_data.get('district', ''),
                'location_data': json.dumps(location_data),
                'source': location_data.get('source', 'india_post_api'),
                'created_at': datetime.now().isoformat(),
                'ttl': ttl
            }
        )
        logger.info(f"Saved pincode {pincode} location to DB: {location_data.get('district')}, {location_data.get('state')}")
        return True
    except Exception as e:
        logger.error(f"Error saving pincode location to DB: {e}")
        return False


def learn_pincode_location(pincode: str) -> Optional[Dict[str, Any]]:
    """
    Learn full location details for a pincode.
    First checks DynamoDB, then fetches from India Post API if not found.
    
    Returns:
        Dict with state, district, post offices, coordinates, etc.
    """
    # First check if already in DB
    location = get_pincode_location(pincode)
    if location:
        logger.info(f"Pincode {pincode} location found in learning DB")
        return location
    
    # Fetch from India Post API
    location_details = fetch_pincode_details(pincode)
    if location_details:
        # Save to DB
        save_pincode_location(pincode, location_details)
        
        # Also try to get coordinates and save them
        coords = geocode_indian_pincode(pincode)
        if coords:
            save_pincode_coordinates(
                pincode=pincode,
                latitude=coords['latitude'],
                longitude=coords['longitude'],
                source='nominatim_for_india_post',
                location_name=f"{location_details.get('primary_location')}, {location_details.get('district')}"
            )
            # Add coordinates to returned data
            location_details['latitude'] = coords['latitude']
            location_details['longitude'] = coords['longitude']
        
        return location_details
    
    return None


def learn_pincode(pincode: str) -> Optional[Tuple[float, float]]:
    """
    Learn a new pincode by geocoding and storing it.
    
    Returns:
        Tuple of (latitude, longitude) or None if failed
    """
    # First check if already in DB
    coords = get_pincode_coordinates(pincode)
    if coords:
        logger.info(f"Pincode {pincode} found in learning DB")
        return coords
    
    # Geocode the pincode
    result = geocode_indian_pincode(pincode)
    if result:
        # Save to DB
        save_pincode_coordinates(
            pincode=pincode,
            latitude=result['latitude'],
            longitude=result['longitude'],
            source=result.get('source', 'geocoded'),
            location_name=result.get('display_name')
        )
        return (result['latitude'], result['longitude'])
    
    return None


# ==================== SOIL PROFILE LEARNING ====================

def get_soil_profile(region: str) -> Optional[Dict[str, Any]]:
    """
    Get soil profile for a region from DynamoDB.
    
    Args:
        region: State or district name (lowercase, underscored)
    
    Returns:
        Soil profile dict or None
    """
    table = _get_table()
    if table is None:
        return None
    
    try:
        response = table.get_item(
            Key={
                'pk': f'SOIL#{region.lower().replace(" ", "_")}',
                'sk': 'PROFILE'
            }
        )
        item = response.get('Item')
        if item and 'profile_data' in item:
            return json.loads(item['profile_data'])
        return None
    except Exception as e:
        logger.warning(f"Error getting soil profile from DB: {e}")
        return None


def save_soil_profile(
    region: str,
    profile: Dict[str, Any],
    source: str = "learned"
) -> bool:
    """
    Save a soil profile to DynamoDB.
    
    Args:
        region: State or district name
        profile: Soil profile data dict
        source: How profile was obtained
    
    Returns:
        True if saved successfully
    """
    table = _get_table()
    if table is None:
        return False
    
    try:
        region_key = region.lower().replace(" ", "_")
        
        # Set TTL to 2 years for soil data (changes slowly)
        ttl = int((datetime.now() + timedelta(days=730)).timestamp())
        
        table.put_item(
            Item={
                'pk': f'SOIL#{region_key}',
                'sk': 'PROFILE',
                'region': region_key,
                'profile_data': json.dumps(profile),
                'source': source,
                'created_at': datetime.now().isoformat(),
                'ttl': ttl
            }
        )
        logger.info(f"Saved soil profile for {region} to DB")
        return True
    except Exception as e:
        logger.error(f"Error saving soil profile to DB: {e}")
        return False


def learn_soil_from_query(
    region: str,
    soil_type: str,
    ph_level: float = None,
    characteristics: Dict[str, Any] = None,
    source: str = "query_extracted"
) -> bool:
    """
    Learn soil information from a user query and store it.
    
    Args:
        region: Location/region name
        soil_type: Type of soil (loam, clay, etc.)
        ph_level: pH level if mentioned
        characteristics: Other soil characteristics
        source: Where the data came from
    
    Returns:
        True if saved successfully
    """
    # Build profile from extracted data
    profile = {
        "primary_soil": soil_type,
        "ph_range": [ph_level - 0.5, ph_level + 0.5] if ph_level else [6.0, 7.5],
        "confidence": 0.6,  # Lower confidence for learned data
        "source": source,
        "learned_at": datetime.now().isoformat()
    }
    
    if characteristics:
        profile.update(characteristics)
    
    return save_soil_profile(region, profile, source)


# ==================== WEATHER LEARNING ====================

def get_weather_profile(region: str) -> Optional[Dict[str, Any]]:
    """
    Get learned weather profile for a region from DynamoDB.
    """
    table = _get_table()
    if table is None:
        return None
    
    try:
        response = table.get_item(
            Key={
                'pk': f'WEATHER#{region.lower().replace(" ", "_")}',
                'sk': 'PROFILE'
            }
        )
        item = response.get('Item')
        if item and 'profile_data' in item:
            return json.loads(item['profile_data'])
        return None
    except Exception as e:
        logger.warning(f"Error getting weather profile from DB: {e}")
        return None


def save_weather_observation(
    region: str,
    season: str,
    temp_min: float,
    temp_max: float,
    rainfall: float,
    humidity: float,
    source: str = "api_observed"
) -> bool:
    """
    Save weather observation to help build regional profiles.
    """
    table = _get_table()
    if table is None:
        return False
    
    try:
        region_key = region.lower().replace(" ", "_")
        
        # Use date as sort key to track historical observations
        date_key = datetime.now().strftime("%Y-%m")
        
        table.put_item(
            Item={
                'pk': f'WEATHER#{region_key}',
                'sk': f'OBS#{season}#{date_key}',
                'region': region_key,
                'season': season,
                'temp_min': str(temp_min),
                'temp_max': str(temp_max),
                'rainfall': str(rainfall),
                'humidity': str(humidity),
                'source': source,
                'observed_at': datetime.now().isoformat()
            }
        )
        logger.info(f"Saved weather observation for {region}/{season}")
        return True
    except Exception as e:
        logger.error(f"Error saving weather observation: {e}")
        return False


# ==================== UTILITY FUNCTIONS ====================

def is_dynamodb_available() -> bool:
    """Check if DynamoDB is available and table exists."""
    table = _get_table()
    if table is None:
        return False
    try:
        table.table_status
        return True
    except Exception:
        return False


def get_learning_stats() -> Dict[str, int]:
    """Get statistics about learned data."""
    table = _get_table()
    if table is None:
        return {"pincodes": 0, "soil_profiles": 0, "weather_observations": 0}
    
    try:
        # This is a simplified count - for production, use a counter
        return {
            "pincodes": "unknown",
            "soil_profiles": "unknown", 
            "weather_observations": "unknown",
            "table_available": True
        }
    except Exception as e:
        return {"error": str(e), "table_available": False}
