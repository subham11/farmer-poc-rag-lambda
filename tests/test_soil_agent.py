"""
Unit tests for Soil Agent
"""

import pytest
from unittest.mock import patch, MagicMock
from src.agents.soil_agent import analyze_soil


class TestSoilAgent:
    """Test cases for soil analysis agent."""

    @patch('src.agents.soil_agent.retrieve_documents')
    @patch('src.agents.soil_agent.logger')
    def test_analyze_soil_clay_type(self, mock_logger, mock_retrieve):
        """Test soil analysis for clay soil type."""
        # Mock RAG retrieval
        mock_retrieve.return_value = [
            {"content": "Clay soil has poor drainage and high nutrient retention"}
        ]

        query = "my soil is clay with pH 6.5"
        result = analyze_soil(query)

        assert result["soil_type"] == "clay"
        assert result["ph_level"] == 6.5
        assert result["health_score"] >= 1
        assert result["health_score"] <= 10
        assert isinstance(result["constraints"], list)
        assert isinstance(result["recommendations"], list)
        assert "drainage" in str(result["constraints"]).lower()

    @patch('src.agents.soil_agent.retrieve_documents')
    @patch('src.agents.soil_agent.logger')
    def test_analyze_soil_sandy_type(self, mock_logger, mock_retrieve):
        """Test soil analysis for sandy soil type."""
        mock_retrieve.return_value = [
            {"content": "Sandy soil drains quickly but has low nutrient retention"}
        ]

        query = "I have sandy soil"
        result = analyze_soil(query)

        assert result["soil_type"] == "sandy"
        assert result["health_score"] >= 1
        assert result["health_score"] <= 10
        assert isinstance(result["constraints"], list)
        assert isinstance(result["recommendations"], list)

    @patch('src.agents.soil_agent.retrieve_documents')
    @patch('src.agents.soil_agent.logger')
    def test_analyze_soil_acidic_ph(self, mock_logger, mock_retrieve):
        """Test soil analysis for acidic pH."""
        mock_retrieve.return_value = []

        query = "soil pH is 5.2"
        result = analyze_soil(query)

        assert result["ph_level"] == 5.2
        # Acidic soil adds constraint about liming
        assert any("acidic" in constraint.lower() for constraint in result["constraints"])

    @patch('src.agents.soil_agent.retrieve_documents')
    @patch('src.agents.soil_agent.logger')
    def test_analyze_soil_alkaline_ph(self, mock_logger, mock_retrieve):
        """Test soil analysis for alkaline pH."""
        mock_retrieve.return_value = []

        query = "soil pH is 8.5"
        result = analyze_soil(query)

        assert result["ph_level"] == 8.5
        # Alkaline soil adds constraint about micronutrient deficiency
        assert any("alkaline" in constraint.lower() for constraint in result["constraints"])

    @patch('src.agents.soil_agent.retrieve_documents')
    @patch('src.agents.soil_agent.logger')
    def test_analyze_soil_optimal_conditions(self, mock_logger, mock_retrieve):
        """Test soil analysis for optimal conditions."""
        mock_retrieve.return_value = []

        query = "loam soil with pH 7.0"
        result = analyze_soil(query)

        assert result["soil_type"] == "loam"
        assert result["ph_level"] == 7.0
        assert result["health_score"] > 7  # Higher score for optimal conditions

    @patch('src.agents.soil_agent.retrieve_documents')
    @patch('src.agents.soil_agent.logger')
    def test_analyze_soil_with_npk_values(self, mock_logger, mock_retrieve):
        """Test soil analysis with NPK values."""
        mock_retrieve.return_value = []

        query = "soil has nitrogen 50, phosphorus 30, potassium 40"
        result = analyze_soil(query)

        # NPK extraction is simplified in current implementation
        assert "npk_levels" in result
        assert isinstance(result["npk_levels"], dict)
        assert "nitrogen" in result["npk_levels"]
        assert "phosphorus" in result["npk_levels"]
        assert "potassium" in result["npk_levels"]

    @patch('src.agents.soil_agent.retrieve_documents')
    @patch('src.agents.soil_agent.logger')
    def test_analyze_soil_error_handling(self, mock_logger, mock_retrieve):
        """Test error handling in soil analysis."""
        mock_retrieve.side_effect = Exception("RAG service unavailable")

        query = "clay soil analysis"
        result = analyze_soil(query)

        assert "error" in result
        assert result["soil_type"] == "unknown"
        # Error case returns a moderate score with low confidence
        assert result["health_score"] >= 1
        assert result["health_score"] <= 10
        assert "Analysis failed" in str(result["constraints"])

    @patch('src.agents.soil_agent.retrieve_documents')
    @patch('src.agents.soil_agent.logger')
    def test_analyze_soil_empty_query(self, mock_logger, mock_retrieve):
        """Test soil analysis with empty query."""
        mock_retrieve.return_value = []

        query = ""
        result = analyze_soil(query)

        # Empty query falls back to location profile (default is loam)
        assert result["soil_type"] in ["unknown", "loam"]
        assert result["ph_level"] == 7.0
        assert result["health_score"] >= 1
        assert result["health_score"] <= 10

    def test_calculate_soil_health_bounds(self):
        """Test soil health score stays within bounds."""
        from src.agents.soil_agent import _calculate_soil_health

        # Test various soil data combinations
        test_cases = [
            {"type": "loam", "ph": 7.0},  # Optimal
            {"type": "clay", "ph": 5.0},  # Poor
            {"type": "sandy", "ph": 9.0}, # Poor
            {"type": "unknown", "ph": 7.0} # Average
        ]

        for soil_data in test_cases:
            score, confidence = _calculate_soil_health(soil_data)
            assert 1 <= score <= 10, f"Score {score} out of bounds for {soil_data}"
            assert 0 <= confidence <= 1, f"Confidence {confidence} out of bounds for {soil_data}"

    def test_identify_constraints_return_type(self):
        """Test constraints identification returns proper format."""
        from src.agents.soil_agent import _identify_constraints

        soil_data = {"type": "clay", "ph": 6.0}
        constraints = _identify_constraints(soil_data)

        assert isinstance(constraints, list)
        assert len(constraints) > 0

    def test_generate_recommendations_return_type(self):
        """Test recommendations generation returns proper format."""
        from src.agents.soil_agent import _generate_recommendations

        soil_data = {"type": "clay", "ph": 6.0}
        recommendations = _generate_recommendations(soil_data)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0