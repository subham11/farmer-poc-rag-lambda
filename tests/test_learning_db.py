"""
Unit tests for the Learning Database module.

Tests the self-learning functionality including:
- Pincode geocoding and storage
- Soil profile learning and retrieval
- Weather observation storage
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestLearningDBGeocode:
    """Tests for pincode geocoding functionality."""
    
    @patch('utils.learning_db.urllib.request.urlopen')
    def test_geocode_indian_pincode_success(self, mock_urlopen):
        """Test successful geocoding of a pincode."""
        from utils.learning_db import geocode_indian_pincode
        
        # Mock successful Nominatim response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([{
            "lat": "18.5204",
            "lon": "73.8567",
            "display_name": "Pune, Maharashtra, India"
        }]).encode()
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = geocode_indian_pincode("411001")
        
        assert result is not None
        assert "latitude" in result
        assert "longitude" in result
        assert abs(result["latitude"] - 18.5204) < 0.01
        assert abs(result["longitude"] - 73.8567) < 0.01
        assert "display_name" in result
    
    @patch('utils.learning_db.urllib.request.urlopen')
    def test_geocode_indian_pincode_not_found(self, mock_urlopen):
        """Test geocoding when pincode is not found."""
        from utils.learning_db import geocode_indian_pincode
        
        # Mock empty response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([]).encode()
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = geocode_indian_pincode("999999")
        
        assert result is None
    
    @patch('utils.learning_db.urllib.request.urlopen')
    def test_geocode_network_error(self, mock_urlopen):
        """Test geocoding handles network errors gracefully."""
        from utils.learning_db import geocode_indian_pincode
        import urllib.error
        
        mock_urlopen.side_effect = urllib.error.URLError("Network error")
        
        result = geocode_indian_pincode("411001")
        
        assert result is None


class TestLearningDBDynamoDB:
    """Tests for DynamoDB operations (mocked)."""
    
    @patch('utils.learning_db._get_table')
    def test_get_pincode_coordinates_found(self, mock_get_table):
        """Test retrieving pincode from DB when found."""
        from utils.learning_db import get_pincode_coordinates
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'pk': 'PINCODE#411001',
                'sk': 'COORDS',
                'latitude': '18.5204',
                'longitude': '73.8567'
            }
        }
        mock_get_table.return_value = mock_table
        
        result = get_pincode_coordinates("411001")
        
        assert result is not None
        assert result[0] == 18.5204
        assert result[1] == 73.8567
    
    @patch('utils.learning_db._get_table')
    def test_get_pincode_coordinates_not_found(self, mock_get_table):
        """Test retrieving pincode when not in DB."""
        from utils.learning_db import get_pincode_coordinates
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table
        
        result = get_pincode_coordinates("999999")
        
        assert result is None
    
    @patch('utils.learning_db._get_table')
    def test_save_pincode_coordinates_success(self, mock_get_table):
        """Test saving pincode coordinates to DB."""
        from utils.learning_db import save_pincode_coordinates
        
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        
        result = save_pincode_coordinates(
            pincode="411001",
            latitude=18.5204,
            longitude=73.8567,
            source="geocoded",
            location_name="Pune, Maharashtra"
        )
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert item['pk'] == 'PINCODE#411001'
        assert item['sk'] == 'COORDS'
        assert item['latitude'] == '18.5204'
        assert item['longitude'] == '73.8567'
    
    @patch('utils.learning_db._get_table')
    def test_save_pincode_no_table(self, mock_get_table):
        """Test saving pincode when DynamoDB is not available."""
        from utils.learning_db import save_pincode_coordinates
        
        mock_get_table.return_value = None
        
        result = save_pincode_coordinates(
            pincode="411001",
            latitude=18.5204,
            longitude=73.8567
        )
        
        assert result is False


class TestLearningDBSoilProfile:
    """Tests for soil profile learning functionality."""
    
    @patch('utils.learning_db._get_table')
    def test_get_soil_profile_found(self, mock_get_table):
        """Test retrieving soil profile from DB."""
        from utils.learning_db import get_soil_profile
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'pk': 'SOIL#maharashtra',
                'sk': 'PROFILE',
                'profile_data': json.dumps({
                    'primary_soil': 'black_cotton',
                    'ph_range': [7.0, 8.0],
                    'confidence': 0.7
                })
            }
        }
        mock_get_table.return_value = mock_table
        
        result = get_soil_profile("maharashtra")
        
        assert result is not None
        assert result['primary_soil'] == 'black_cotton'
        assert result['confidence'] == 0.7
    
    @patch('utils.learning_db._get_table')
    def test_get_soil_profile_not_found(self, mock_get_table):
        """Test retrieving soil profile when not in DB."""
        from utils.learning_db import get_soil_profile
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_get_table.return_value = mock_table
        
        result = get_soil_profile("unknown_region")
        
        assert result is None
    
    @patch('utils.learning_db._get_table')
    def test_save_soil_profile_success(self, mock_get_table):
        """Test saving soil profile to DB."""
        from utils.learning_db import save_soil_profile
        
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        
        profile = {
            "primary_soil": "loam",
            "ph_range": [6.5, 7.5],
            "confidence": 0.8
        }
        
        result = save_soil_profile("pune_district", profile, "query_extracted")
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert item['pk'] == 'SOIL#pune_district'
        assert item['sk'] == 'PROFILE'
        assert item['source'] == 'query_extracted'
    
    @patch('utils.learning_db._get_table')
    def test_learn_soil_from_query(self, mock_get_table):
        """Test learning soil info from user query."""
        from utils.learning_db import learn_soil_from_query
        
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        
        result = learn_soil_from_query(
            region="nashik",
            soil_type="loam",
            ph_level=6.8,
            characteristics={"organic_matter": 0.6}
        )
        
        assert result is True
        mock_table.put_item.assert_called_once()


class TestLearningDBWeather:
    """Tests for weather observation learning functionality."""
    
    @patch('utils.learning_db._get_table')
    def test_save_weather_observation(self, mock_get_table):
        """Test saving weather observation to DB."""
        from utils.learning_db import save_weather_observation
        
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        
        result = save_weather_observation(
            region="Maharashtra",
            season="kharif",
            temp_min=24.0,
            temp_max=32.0,
            rainfall=150.0,
            humidity=75.0
        )
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert item['pk'] == 'WEATHER#maharashtra'
        assert item['region'] == 'maharashtra'
        assert item['season'] == 'kharif'


class TestLearnPincode:
    """Tests for the high-level learn_pincode function."""
    
    @patch('utils.learning_db.get_pincode_coordinates')
    @patch('utils.learning_db.geocode_indian_pincode')
    @patch('utils.learning_db.save_pincode_coordinates')
    def test_learn_pincode_already_known(
        self, mock_save, mock_geocode, mock_get
    ):
        """Test learn_pincode when pincode already exists in DB."""
        from utils.learning_db import learn_pincode
        
        mock_get.return_value = (18.5204, 73.8567)
        
        result = learn_pincode("411001")
        
        assert result == (18.5204, 73.8567)
        mock_geocode.assert_not_called()
        mock_save.assert_not_called()
    
    @patch('utils.learning_db.get_pincode_coordinates')
    @patch('utils.learning_db.geocode_indian_pincode')
    @patch('utils.learning_db.save_pincode_coordinates')
    def test_learn_pincode_geocode_and_save(
        self, mock_save, mock_geocode, mock_get
    ):
        """Test learn_pincode geocodes and saves new pincode."""
        from utils.learning_db import learn_pincode
        
        mock_get.return_value = None
        mock_geocode.return_value = {
            'latitude': 19.0760,
            'longitude': 72.8777,
            'display_name': 'Mumbai, Maharashtra',
            'source': 'nominatim_geocoded'
        }
        mock_save.return_value = True
        
        result = learn_pincode("400001")
        
        assert result == (19.0760, 72.8777)
        mock_geocode.assert_called_once_with("400001")
        mock_save.assert_called_once()
    
    @patch('utils.learning_db.get_pincode_coordinates')
    @patch('utils.learning_db.geocode_indian_pincode')
    def test_learn_pincode_geocode_fails(self, mock_geocode, mock_get):
        """Test learn_pincode when geocoding fails."""
        from utils.learning_db import learn_pincode
        
        mock_get.return_value = None
        mock_geocode.return_value = None
        
        result = learn_pincode("999999")
        
        assert result is None


class TestDynamoDBAvailability:
    """Tests for DynamoDB availability checking."""
    
    @patch('utils.learning_db._get_table')
    def test_is_dynamodb_available_true(self, mock_get_table):
        """Test checking DynamoDB availability when available."""
        from utils.learning_db import is_dynamodb_available
        
        mock_table = MagicMock()
        mock_table.table_status = 'ACTIVE'
        mock_get_table.return_value = mock_table
        
        result = is_dynamodb_available()
        
        assert result is True
    
    @patch('utils.learning_db._get_table')
    def test_is_dynamodb_available_no_table(self, mock_get_table):
        """Test checking DynamoDB availability when no table."""
        from utils.learning_db import is_dynamodb_available
        
        mock_get_table.return_value = None
        
        result = is_dynamodb_available()
        
        assert result is False


class TestIndiaPostAPI:
    """Tests for India Post API integration."""
    
    @patch('utils.learning_db.urllib.request.urlopen')
    def test_fetch_pincode_details_success(self, mock_urlopen):
        """Test successful fetch from India Post API."""
        from utils.learning_db import fetch_pincode_details
        
        # Mock successful India Post API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([{
            "Status": "Success",
            "Message": "Number of pincode(s) found:1",
            "PostOffice": [
                {
                    "Name": "Shivajinagar",
                    "State": "Maharashtra",
                    "District": "Pune",
                    "Division": "Pune",
                    "Region": "Pune Region",
                    "Circle": "Maharashtra",
                    "Block": "Pune City",
                    "BranchType": "Head Post Office",
                    "DeliveryStatus": "Delivery"
                },
                {
                    "Name": "Camp",
                    "State": "Maharashtra",
                    "District": "Pune",
                    "Division": "Pune",
                    "Region": "Pune Region",
                    "Circle": "Maharashtra",
                    "Block": "Pune City",
                    "BranchType": "Sub Post Office",
                    "DeliveryStatus": "Non-Delivery"
                }
            ]
        }]).encode()
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = fetch_pincode_details("411001")
        
        assert result is not None
        assert result["state"] == "Maharashtra"
        assert result["district"] == "Pune"
        assert result["pincode"] == "411001"
        assert result["primary_location"] == "Shivajinagar"
        assert len(result["post_offices"]) == 2
        assert result["source"] == "india_post_api"
    
    @patch('utils.learning_db.urllib.request.urlopen')
    def test_fetch_pincode_details_not_found(self, mock_urlopen):
        """Test India Post API when pincode is not found."""
        from utils.learning_db import fetch_pincode_details
        
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([{
            "Status": "Error",
            "Message": "No records found",
            "PostOffice": None
        }]).encode()
        mock_response.__enter__ = lambda s: mock_response
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = fetch_pincode_details("999999")
        
        assert result is None
    
    @patch('utils.learning_db.urllib.request.urlopen')
    def test_fetch_pincode_details_network_error(self, mock_urlopen):
        """Test India Post API handles network errors."""
        from utils.learning_db import fetch_pincode_details
        import urllib.error
        
        mock_urlopen.side_effect = urllib.error.URLError("Network error")
        
        result = fetch_pincode_details("411001")
        
        assert result is None
    
    @patch('utils.learning_db._get_table')
    def test_get_pincode_location_found(self, mock_get_table):
        """Test getting pincode location from DB."""
        from utils.learning_db import get_pincode_location
        
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'pk': 'PINCODE#411001',
                'sk': 'LOCATION',
                'location_data': json.dumps({
                    'state': 'Maharashtra',
                    'district': 'Pune',
                    'pincode': '411001'
                })
            }
        }
        mock_get_table.return_value = mock_table
        
        result = get_pincode_location("411001")
        
        assert result is not None
        assert result["state"] == "Maharashtra"
        assert result["district"] == "Pune"
    
    @patch('utils.learning_db._get_table')
    def test_save_pincode_location_success(self, mock_get_table):
        """Test saving pincode location to DB."""
        from utils.learning_db import save_pincode_location
        
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        
        location_data = {
            "pincode": "411001",
            "state": "Maharashtra",
            "district": "Pune",
            "primary_location": "Shivajinagar",
            "source": "india_post_api"
        }
        
        result = save_pincode_location("411001", location_data)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Verify item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        assert item['pk'] == 'PINCODE#411001'
        assert item['sk'] == 'LOCATION'
        assert item['state'] == 'Maharashtra'
        assert item['district'] == 'Pune'


class TestLearnPincodeLocation:
    """Tests for the learn_pincode_location function."""
    
    @patch('utils.learning_db.get_pincode_location')
    def test_learn_pincode_location_already_known(self, mock_get_location):
        """Test learn_pincode_location when already in DB."""
        from utils.learning_db import learn_pincode_location
        
        mock_get_location.return_value = {
            'state': 'Maharashtra',
            'district': 'Pune',
            'pincode': '411001'
        }
        
        result = learn_pincode_location("411001")
        
        assert result is not None
        assert result["state"] == "Maharashtra"
        mock_get_location.assert_called_once()
    
    @patch('utils.learning_db.get_pincode_location')
    @patch('utils.learning_db.fetch_pincode_details')
    @patch('utils.learning_db.save_pincode_location')
    @patch('utils.learning_db.geocode_indian_pincode')
    @patch('utils.learning_db.save_pincode_coordinates')
    def test_learn_pincode_location_fetch_and_save(
        self, mock_save_coords, mock_geocode, mock_save_loc, mock_fetch, mock_get
    ):
        """Test learn_pincode_location fetches from API and saves."""
        from utils.learning_db import learn_pincode_location
        
        mock_get.return_value = None
        mock_fetch.return_value = {
            'state': 'Maharashtra',
            'district': 'Pune',
            'pincode': '411001',
            'primary_location': 'Shivajinagar'
        }
        mock_save_loc.return_value = True
        mock_geocode.return_value = {
            'latitude': 18.5204,
            'longitude': 73.8567
        }
        mock_save_coords.return_value = True
        
        result = learn_pincode_location("411001")
        
        assert result is not None
        assert result["state"] == "Maharashtra"
        assert result["latitude"] == 18.5204
        mock_fetch.assert_called_once_with("411001")
        mock_save_loc.assert_called_once()
        mock_geocode.assert_called_once()
        mock_save_coords.assert_called_once()
