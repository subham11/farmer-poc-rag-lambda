"""
Unit tests for Orchestrator Agent
"""

import pytest
from unittest.mock import patch, MagicMock
from src.agents.orchestrator import orchestrate_query


class TestOrchestratorAgent:
    """Test cases for orchestrator agent."""

    @patch('src.agents.orchestrator.analyze_soil')
    @patch('src.agents.orchestrator.analyze_weather')
    @patch('src.agents.orchestrator.plan_crops')
    @patch('src.agents.orchestrator.logger')
    def test_orchestrate_full_pipeline(self, mock_logger, mock_plan_crops, mock_weather, mock_soil):
        """Test full orchestration with all agents."""
        # Mock agent responses
        mock_soil.return_value = {
            "soil_type": "loam",
            "ph_level": 7.0,
            "health_score": 8,
            "constraints": [],
            "recommendations": []
        }

        mock_weather.return_value = {
            "season": "kharif",
            "suitability_score": 8,
            "temperature_range": {"min": 25, "max": 35},
            "rainfall_mm": 800,
            "risk_factors": [],
            "optimal_crops": ["rice", "maize"]
        }

        mock_plan_crops.return_value = {
            "recommended_crops": [{"name": "rice", "confidence": 0.9}],
            "alternatives": ["maize"],
            "risks": [],
            "precautions": []
        }

        query = "what crops should I plant in my loam soil for kharif season"
        result = orchestrate_query(query)

        assert result["query"] == query
        assert "soil" in result["agents_invoked"]
        assert "weather" in result["agents_invoked"]
        assert "crop_planning" in result["agents_invoked"]
        assert result["soil_data"] is not None
        assert result["weather_data"] is not None
        assert result["crop_plan"] is not None
        assert "llm_prompt_input" in result

    @patch('src.agents.orchestrator.analyze_soil')
    @patch('src.agents.orchestrator.analyze_weather')
    @patch('src.agents.orchestrator.plan_crops')
    @patch('src.agents.orchestrator.logger')
    def test_orchestrate_soil_only_query(self, mock_logger, mock_plan_crops, mock_weather, mock_soil):
        """Test orchestration for soil-only query."""
        mock_soil.return_value = {
            "soil_type": "clay",
            "ph_level": 6.5,
            "health_score": 7,
            "constraints": ["Poor drainage"],
            "recommendations": ["Add organic matter"]
        }

        query = "my soil is clay with pH 6.5, how can I improve it"
        result = orchestrate_query(query)

        assert "soil" in result["agents_invoked"]
        assert "weather" not in result["agents_invoked"]
        assert "crop_planning" not in result["agents_invoked"]
        assert result["soil_data"] is not None
        assert result["weather_data"] is None
        assert result["crop_plan"] is None

    @patch('src.agents.orchestrator.analyze_soil')
    @patch('src.agents.orchestrator.analyze_weather')
    @patch('src.agents.orchestrator.plan_crops')
    @patch('src.agents.orchestrator.logger')
    def test_orchestrate_weather_only_query(self, mock_logger, mock_plan_crops, mock_weather, mock_soil):
        """Test orchestration for weather-only query."""
        mock_weather.return_value = {
            "season": "rabi",
            "suitability_score": 7,
            "temperature_range": {"min": 10, "max": 25},
            "rainfall_mm": 50,
            "risk_factors": ["Low rainfall"],
            "optimal_crops": ["wheat"]
        }

        query = "what is the weather like for rabi season"
        result = orchestrate_query(query)

        assert "weather" in result["agents_invoked"]
        assert "soil" not in result["agents_invoked"]
        assert "crop_planning" not in result["agents_invoked"]
        assert result["weather_data"] is not None
        assert result["soil_data"] is None
        assert result["crop_plan"] is None

    @patch('src.agents.orchestrator.analyze_soil')
    @patch('src.agents.orchestrator.analyze_weather')
    @patch('src.agents.orchestrator.plan_crops')
    @patch('src.agents.orchestrator.logger')
    def test_orchestrate_crop_planning_query(self, mock_logger, mock_plan_crops, mock_weather, mock_soil):
        """Test orchestration for crop planning query."""
        mock_soil.return_value = {
            "soil_type": "loam",
            "ph_level": 7.0,
            "health_score": 8,
            "constraints": [],
            "recommendations": []
        }

        mock_weather.return_value = {
            "season": "kharif",
            "suitability_score": 8,
            "temperature_range": {"min": 25, "max": 35},
            "rainfall_mm": 800,
            "risk_factors": [],
            "optimal_crops": ["rice", "maize"]
        }

        mock_plan_crops.return_value = {
            "recommended_crops": [{"name": "rice", "confidence": 0.9}],
            "alternatives": ["maize"],
            "risks": [],
            "precautions": []
        }

        query = "which crops should I plant"
        result = orchestrate_query(query)

        assert "crop_planning" in result["agents_invoked"]
        # Crop planning requires both soil and weather
        assert "soil" in result["agents_invoked"]
        assert "weather" in result["agents_invoked"]
        assert result["crop_plan"] is not None

    @patch('src.agents.orchestrator.analyze_soil')
    @patch('src.agents.orchestrator.analyze_weather')
    @patch('src.agents.orchestrator.plan_crops')
    @patch('src.agents.orchestrator.logger')
    def test_orchestrate_agent_error_handling(self, mock_logger, mock_plan_crops, mock_weather, mock_soil):
        """Test orchestration with agent errors."""
        mock_soil.side_effect = Exception("Soil analysis failed")
        mock_weather.return_value = {
            "season": "kharif",
            "suitability_score": 8,
            "error": "Soil analysis failed"
        }

        query = "crop recommendations"
        result = orchestrate_query(query)

        assert "error" in result
        assert result["agents_invoked"] == []
        assert "Error processing query" in result["llm_prompt_input"]

    @patch('src.agents.orchestrator.logger')
    def test_orchestrate_empty_query(self, mock_logger):
        """Test orchestration with empty query."""
        query = ""
        result = orchestrate_query(query)

        assert result["query"] == ""
        assert "soil" in result["agents_invoked"]
        assert "weather" in result["agents_invoked"]
        assert "crop_planning" in result["agents_invoked"]

    @patch('src.agents.orchestrator.logger')
    def test_orchestrate_vague_query(self, mock_logger):
        """Test orchestration with vague query."""
        query = "help me with farming"
        result = orchestrate_query(query)

        # Should invoke all agents for comprehensive analysis
        assert "soil" in result["agents_invoked"]
        assert "weather" in result["agents_invoked"]
        assert "crop_planning" in result["agents_invoked"]

    def test_analyze_query_intent_soil_keywords(self):
        """Test query intent analysis for soil-related keywords."""
        from src.agents.orchestrator import _analyze_query_intent

        soil_queries = [
            "my soil is clay",
            "soil pH is 6.5",
            "fertile land",
            "ground conditions"
        ]

        for query in soil_queries:
            result = _analyze_query_intent(query)
            # Now returns dict with 'agents' key
            agents = result.get("agents", [])
            assert "soil" in agents, f"Expected 'soil' agent for query: {query}"

    def test_analyze_query_intent_weather_keywords(self):
        """Test query intent analysis for weather-related keywords."""
        from src.agents.orchestrator import _analyze_query_intent

        weather_queries = [
            "kharif season",
            "weather conditions",
            "rainfall this year",
            "temperature for farming"
        ]

        for query in weather_queries:
            result = _analyze_query_intent(query)
            # Now returns dict with 'agents' key
            agents = result.get("agents", [])
            assert "weather" in agents, f"Expected 'weather' agent for query: {query}"

    def test_analyze_query_intent_crop_keywords(self):
        """Test query intent analysis for crop-related keywords."""
        from src.agents.orchestrator import _analyze_query_intent

        crop_queries = [
            "which crops to plant",
            "best crop for my farm",
            "recommend crops",
            "what to grow"
        ]

        for query in crop_queries:
            result = _analyze_query_intent(query)
            # Now returns dict with 'agents' key
            agents = result.get("agents", [])
            assert "crop_planning" in agents, f"Expected 'crop_planning' agent for query: {query}"
            # Crop planning should also invoke soil and weather
            assert "soil" in agents, f"Expected 'soil' agent for crop query: {query}"
            assert "weather" in agents, f"Expected 'weather' agent for crop query: {query}"

    def test_analyze_query_intent_combined_keywords(self):
        """Test query intent analysis for combined keywords."""
        from src.agents.orchestrator import _analyze_query_intent

        query = "what crops should I plant in clay soil during kharif season"
        result = _analyze_query_intent(query)
        # Now returns dict with 'agents' key
        agents = result.get("agents", [])

        assert "soil" in agents
        assert "weather" in agents
        assert "crop_planning" in agents

    def test_analyze_query_intent_no_keywords(self):
        """Test query intent analysis with no specific keywords."""
        from src.agents.orchestrator import _analyze_query_intent

        query = "tell me about farming"
        result = _analyze_query_intent(query)
        # Now returns dict with 'agents' key
        agents = result.get("agents", [])

        # Should default to all agents
        assert "soil" in agents
        assert "weather" in agents
        assert "crop_planning" in agents

    @patch('src.agents.orchestrator.analyze_soil')
    @patch('src.agents.orchestrator.analyze_weather')
    @patch('src.agents.orchestrator.plan_crops')
    def test_generate_llm_prompt_structure(self, mock_plan_crops, mock_weather, mock_soil):
        """Test LLM prompt generation structure."""
        from src.agents.orchestrator import _generate_llm_prompt

        mock_soil.return_value = {
            "soil_type": "loam",
            "ph_level": 7.0,
            "health_score": 8,
            "constraints": ["Minor constraints"],
            "recommendations": ["Regular testing"]
        }

        mock_weather.return_value = {
            "season": "kharif",
            "suitability_score": 8,
            "temperature_range": {"min": 25, "max": 35},
            "rainfall_mm": 800,
            "risk_factors": ["Heavy rain possible"],
            "optimal_crops": ["rice"]
        }

        mock_plan_crops.return_value = {
            "recommended_crops": [{"name": "rice", "confidence": 0.9, "reasoning": "Good fit", "expected_yield": "4-5 tons/ha", "duration_months": 4}],
            "alternatives": ["maize"],
            "risks": ["Pest pressure"],
            "precautions": ["Use pesticides"]
        }

        orchestrator_response = {
            "query": "test query",
            "agents_invoked": ["soil", "weather", "crop_planning"],
            "soil_data": mock_soil.return_value,
            "weather_data": mock_weather.return_value,
            "crop_plan": mock_plan_crops.return_value
        }

        prompt = _generate_llm_prompt(orchestrator_response)

        assert "User Query: test query" in prompt
        assert "SOIL ANALYSIS:" in prompt
        assert "WEATHER ANALYSIS:" in prompt
        assert "CROP RECOMMENDATIONS:" in prompt
        assert "Instructions for Response:" in prompt
        assert "Response:" in prompt

    def test_generate_llm_prompt_partial_data(self):
        """Test LLM prompt generation with partial agent data."""
        from src.agents.orchestrator import _generate_llm_prompt

        orchestrator_response = {
            "query": "soil test",
            "agents_invoked": ["soil"],
            "soil_data": {
                "soil_type": "clay",
                "ph_level": 6.5,
                "health_score": 7,
                "constraints": ["Poor drainage"],
                "recommendations": ["Add organic matter"]
            },
            "weather_data": None,
            "crop_plan": None
        }

        prompt = _generate_llm_prompt(orchestrator_response)

        assert "SOIL ANALYSIS:" in prompt
        assert "WEATHER ANALYSIS:" not in prompt
        assert "CROP RECOMMENDATIONS:" not in prompt

    def test_generate_llm_prompt_empty_data(self):
        """Test LLM prompt generation with no agent data."""
        from src.agents.orchestrator import _generate_llm_prompt

        orchestrator_response = {
            "query": "general question",
            "agents_invoked": [],
            "soil_data": None,
            "weather_data": None,
            "crop_plan": None
        }

        prompt = _generate_llm_prompt(orchestrator_response)

        assert "User Query: general question" in prompt
        assert "Analysis Results:" in prompt
        # Should still have basic structure
        assert "Instructions for Response:" in prompt