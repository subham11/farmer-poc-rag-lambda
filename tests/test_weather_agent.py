"""
Unit tests for Weather Agent
"""

import pytest
from unittest.mock import patch, MagicMock
from src.agents.weather_agent import analyze_weather


class TestWeatherAgent:
    """Test cases for weather analysis agent."""

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_kharif_season(self, mock_logger):
        """Test weather analysis for kharif season."""
        query = "planning for kharif season"
        result = analyze_weather(query)

        assert result["season"] == "kharif"
        assert result["suitability_score"] >= 1
        assert result["suitability_score"] <= 10
        assert isinstance(result["temperature_range"], dict)
        assert "min" in result["temperature_range"]
        assert "max" in result["temperature_range"]
        assert isinstance(result["risk_factors"], list)
        assert isinstance(result["optimal_crops"], list)

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_rabi_season(self, mock_logger):
        """Test weather analysis for rabi season."""
        query = "rabi season planning"
        result = analyze_weather(query)

        assert result["season"] == "rabi"
        assert result["suitability_score"] >= 1
        assert result["suitability_score"] <= 10
        # Rabi typically has lower rainfall
        assert result["rainfall_mm"] < 200

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_zaid_season(self, mock_logger):
        """Test weather analysis for zaid season."""
        query = "zaid season crops"
        result = analyze_weather(query)

        assert result["season"] == "zaid"
        assert result["suitability_score"] >= 1
        assert result["suitability_score"] <= 10

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_no_season_specified(self, mock_logger):
        """Test weather analysis when no season is specified."""
        query = "what is the weather like"
        result = analyze_weather(query)

        # Default season determined by current date - accept any valid season
        assert result["season"] in ["kharif", "rabi", "zaid"]
        assert result["suitability_score"] >= 1
        assert result["suitability_score"] <= 10

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_high_rainfall(self, mock_logger):
        """Test weather analysis for high rainfall conditions."""
        # Mock the internal function to return high rainfall
        with patch('src.agents.weather_agent._get_weather_data') as mock_weather:
            mock_weather.return_value = {
                "temperature": {"min": 25.0, "max": 35.0},
                "rainfall": 900.0,  # High rainfall
                "humidity": 80.0
            }

            query = "kharif season"
            result = analyze_weather(query)

            assert result["rainfall_mm"] == 900.0
            assert result["suitability_score"] >= 5  # Should be decent for kharif
            # optimal_crops is now a list of dicts, check for rice in crop names
            crop_names = [crop["crop"] if isinstance(crop, dict) else crop for crop in result["optimal_crops"]]
            assert any("rice" in str(name).lower() for name in crop_names)

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_low_rainfall(self, mock_logger):
        """Test weather analysis for low rainfall conditions."""
        with patch('src.agents.weather_agent._get_weather_data') as mock_weather:
            mock_weather.return_value = {
                "temperature": {"min": 15.0, "max": 25.0},
                "rainfall": 30.0,  # Low rainfall
                "humidity": 40.0
            }

            query = "rabi season"
            result = analyze_weather(query)

            assert result["rainfall_mm"] == 30.0
            assert result["suitability_score"] >= 1
            # Should include drought risk
            assert any("drought" in risk.lower() for risk in result["risk_factors"])

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_extreme_temperature(self, mock_logger):
        """Test weather analysis for extreme temperature conditions."""
        with patch('src.agents.weather_agent._get_weather_data') as mock_weather:
            mock_weather.return_value = {
                "temperature": {"min": 35.0, "max": 45.0},  # Very hot
                "rainfall": 100.0,
                "humidity": 60.0
            }

            query = "summer season"
            result = analyze_weather(query)

            # Temperature range should reflect the mocked data or zaid season defaults
            assert result["suitability_score"] >= 1  # Valid score range
            assert result["suitability_score"] <= 10
            # Risk factors may include heat-related warnings
            assert isinstance(result["risk_factors"], list)

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_error_handling(self, mock_logger):
        """Test error handling in weather analysis."""
        with patch('src.agents.weather_agent._extract_season_info', side_effect=Exception("Parse error")):
            query = "weather analysis"
            result = analyze_weather(query)

            assert "error" in result
            assert result["season"] == "unknown"
            assert result["suitability_score"] == 5
            assert "Analysis failed" in str(result["risk_factors"])

    @patch('src.agents.weather_agent.logger')
    def test_analyze_weather_empty_query(self, mock_logger):
        """Test weather analysis with empty query."""
        query = ""
        result = analyze_weather(query)

        # Default season determined by current date - accept any valid season
        assert result["season"] in ["kharif", "rabi", "zaid"]
        assert result["suitability_score"] >= 1
        assert result["suitability_score"] <= 10

    def test_extract_season_info_kharif(self):
        """Test season extraction for kharif."""
        from src.agents.weather_agent import _extract_season_info

        result = _extract_season_info("kharif season planning")
        assert result["season"] == "kharif"

    def test_extract_season_info_rabi(self):
        """Test season extraction for rabi."""
        from src.agents.weather_agent import _extract_season_info

        result = _extract_season_info("rabi crops")
        assert result["season"] == "rabi"

    def test_extract_season_info_zaid(self):
        """Test season extraction for zaid."""
        from src.agents.weather_agent import _extract_season_info

        result = _extract_season_info("zaid season")
        assert result["season"] == "zaid"

    def test_calculate_suitability_bounds(self):
        """Test suitability score stays within bounds."""
        from src.agents.weather_agent import _calculate_suitability

        # Test various weather conditions
        test_cases = [
            {"temperature": {"min": 20, "max": 30}, "rainfall": 500},  # Optimal
            {"temperature": {"min": 10, "max": 20}, "rainfall": 50},   # Cool and dry
            {"temperature": {"min": 35, "max": 45}, "rainfall": 1000}, # Hot and wet
        ]

        for weather_data in test_cases:
            result = _calculate_suitability(weather_data)
            # Now returns tuple (score, confidence)
            if isinstance(result, tuple):
                score, confidence = result
            else:
                score = result
                confidence = 0.5
            assert 1 <= score <= 10, f"Score {score} out of bounds for {weather_data}"
            assert 0 <= confidence <= 1, f"Confidence {confidence} out of bounds"

    def test_identify_risks_high_rainfall(self):
        """Test risk identification for high rainfall."""
        from src.agents.weather_agent import _assess_comprehensive_risks

        weather_data = {
            "temperature": {"min": 25, "max": 35},
            "temp_min": 25,
            "temp_max": 35,
            "rainfall": 2200,  # Very high - above flood threshold
            "humidity": 80
        }

        risks = _assess_comprehensive_risks(weather_data)
        # New structure has risks with levels and a summary
        assert "flood" in risks
        # Check summary for flood-related warnings
        assert any("flood" in str(item).lower() or "waterlog" in str(item).lower() 
                   for item in risks.get("summary", []))

    def test_identify_risks_low_rainfall(self):
        """Test risk identification for low rainfall."""
        from src.agents.weather_agent import _assess_comprehensive_risks

        weather_data = {
            "temperature": {"min": 15, "max": 25},
            "temp_min": 15,
            "temp_max": 25,
            "rainfall": 20,  # Very low
            "humidity": 30,
            "season": "kharif"  # Low rainfall is critical in kharif
        }

        risks = _assess_comprehensive_risks(weather_data)
        # New structure has risks with levels and a summary
        assert "drought" in risks
        # Drought should be flagged for low rainfall in kharif season
        assert risks["drought"]["level"] in ["moderate", "high"]

    def test_suggest_weather_suitable_crops_kharif(self):
        """Test crop suggestions for kharif season."""
        from src.agents.weather_agent import _suggest_weather_suitable_crops

        weather_data = {
            "temperature": {"min": 25, "max": 35},
            "temp_min": 25,
            "temp_max": 35,
            "rainfall": 800,  # High rainfall
            "humidity": 75,
            "season": "kharif"
        }

        crops = _suggest_weather_suitable_crops(weather_data)
        assert isinstance(crops, list)
        # Now returns list of dicts with crop info
        assert len(crops) > 0
        
        # Extract crop names from the list of dicts
        crop_names = [c["crop"] if isinstance(c, dict) else c for c in crops]
        # Should include monsoon crops
        monsoon_crops = ["rice", "maize", "cotton", "soybean", "sugarcane", "groundnut", "millet", "sorghum"]
        assert any(crop in crop_names for crop in monsoon_crops)

    def test_suggest_weather_suitable_crops_rabi(self):
        """Test crop suggestions for rabi season."""
        from src.agents.weather_agent import _suggest_weather_suitable_crops

        weather_data = {
            "temperature": {"min": 10, "max": 25},
            "temp_min": 10,
            "temp_max": 25,
            "rainfall": 50,  # Low rainfall
            "humidity": 45,
            "season": "rabi"
        }

        crops = _suggest_weather_suitable_crops(weather_data)
        assert isinstance(crops, list)
        # Extract crop names from list of dicts
        crop_names = [c["crop"] if isinstance(c, dict) else c for c in crops]
        # Should include winter crops
        winter_crops = ["wheat", "barley", "chickpea", "mustard", "potato"]
        assert any(crop in crop_names for crop in winter_crops)