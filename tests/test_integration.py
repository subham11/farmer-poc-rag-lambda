"""
Integration tests for Multi-Agent System
"""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestMultiAgentIntegration:
    """Integration tests for the complete multi-agent system."""

    @patch('src.handler.orchestrate_query')
    @patch('src.handler.call_llm')
    @patch('src.handler.logger')
    def test_handler_with_multi_agent(self, mock_logger, mock_llm, mock_orchestrate):
        """Test main handler integration with multi-agent system."""
        from src.handler import lambda_handler

        # Mock orchestrator response
        mock_orchestrate.return_value = {
            "query": "test query",
            "agents_invoked": ["soil", "weather", "crop_planning"],
            "soil_data": {"soil_type": "loam", "health_score": 8},
            "weather_data": {"season": "kharif", "suitability_score": 8},
            "crop_plan": {"recommended_crops": [{"name": "rice"}]},
            "llm_prompt_input": "Structured prompt for LLM"
        }

        # Mock LLM response
        mock_llm.return_value = "Rice is recommended for your loam soil in kharif season."

        # Test POST request with use_agents=true
        event = {
            "body": json.dumps({
                "question": "what crops should I plant",
                "use_agents": True
            })
        }

        result = lambda_handler(event, {})

        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert "question" in response_body
        assert "answer" in response_body
        assert "agents_used" in response_body
        assert "analysis" in response_body

        # Verify orchestrator was called with query and context
        mock_orchestrate.assert_called_once()
        call_args = mock_orchestrate.call_args
        assert call_args[0][0] == "what crops should I plant"
        # Second arg should be context dict
        assert isinstance(call_args[0][1], dict)
        assert "pincode" in call_args[0][1]
        assert "state" in call_args[0][1]

        # Verify LLM was called with structured prompt
        mock_llm.assert_called_once()

    @patch('src.handler.retrieve_documents')
    @patch('src.handler.build_prompt')
    @patch('src.handler.call_llm')
    @patch('src.handler.logger')
    def test_handler_with_traditional_rag(self, mock_logger, mock_llm, mock_build_prompt, mock_retrieve):
        """Test main handler with traditional RAG (use_agents=false)."""
        from src.handler import lambda_handler

        # Mock traditional RAG components
        mock_retrieve.return_value = [{"content": "test document"}]
        mock_build_prompt.return_value = "test prompt"
        mock_llm.return_value = "test answer"

        # Test POST request with use_agents=false
        event = {
            "body": json.dumps({
                "question": "what is farming",
                "use_agents": False
            })
        }

        result = lambda_handler(event, {})

        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert "question" in response_body
        assert "answer" in response_body
        assert response_body["answer"] == "test answer"

        # Verify traditional RAG components were called
        mock_retrieve.assert_called_once_with("what is farming")
        mock_build_prompt.assert_called_once()
        mock_llm.assert_called_once_with("test prompt")

    @patch('src.handler.orchestrate_query')
    @patch('src.handler.logger')
    def test_handler_multi_agent_error_handling(self, mock_logger, mock_orchestrate):
        """Test error handling in multi-agent mode."""
        from src.handler import lambda_handler

        # Mock orchestrator error
        mock_orchestrate.side_effect = Exception("Agent system unavailable")

        event = {
            "body": json.dumps({
                "question": "test query",
                "use_agents": True
            })
        }

        result = lambda_handler(event, {})

        # Handler returns 500 for unhandled exceptions
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "error" in response_body

    @patch('src.agents.orchestrator.orchestrate_query')
    @patch('src.agents.orchestrator.logger')
    def test_voice_handler_integration(self, mock_logger, mock_orchestrate):
        """Test voice handler integration with multi-agent system."""
        from src.voice.handlers import asr_handler

        # Mock successful ASR
        with patch('src.voice.handlers.asr_router') as mock_router:
            mock_asr = MagicMock()
            mock_asr.transcribe_audio.return_value = {
                "text": "what crops should I plant",
                "provider": "transcribe",
                "language": "en"
            }
            mock_router.transcribe_audio = mock_asr.transcribe_audio

            # Mock rate limiter
            with patch('src.voice.handlers.rate_limiter') as mock_rate_limiter:
                mock_rate_limiter.check_and_increment.return_value = (True, 4, 1800)

                # Mock orchestrator
                mock_orchestrate.return_value = {
                    "query": "what crops should I plant",
                    "agents_invoked": ["soil", "weather", "crop_planning"],
                    "llm_prompt_input": "test prompt"
                }

                event = {
                    "body": json.dumps({
                        "s3_key": "uploads/test/audio.wav",
                        "query_agents": True
                    }),
                    "headers": {"X-Session-Id": "test-session"}
                }

                result = asr_handler(event, {})

                assert result["statusCode"] == 200
                response_body = json.loads(result["body"])
                assert "text" in response_body
                assert "agent_response" in response_body

                # Verify orchestrator was called
                mock_orchestrate.assert_called_once_with("what crops should I plant")

    @patch('src.agents.orchestrator.analyze_soil')
    @patch('src.agents.orchestrator.analyze_weather')
    @patch('src.agents.orchestrator.plan_crops')
    @patch('src.agents.orchestrator.logger')
    def test_full_agent_pipeline_integration(self, mock_logger, mock_plan_crops, mock_weather, mock_soil):
        """Test the complete agent pipeline working together."""
        from src.agents.orchestrator import orchestrate_query

        # Set up realistic mock responses
        mock_soil.return_value = {
            "soil_type": "loam",
            "ph_level": 7.0,
            "health_score": 8,
            "npk_levels": {"nitrogen": 50, "phosphorus": 30, "potassium": 40},
            "constraints": [],
            "recommendations": ["Regular soil testing"]
        }

        mock_weather.return_value = {
            "season": "kharif",
            "temperature_range": {"min": 25, "max": 35},
            "rainfall_mm": 800,
            "humidity_percent": 75,
            "suitability_score": 8,
            "risk_factors": [],
            "optimal_crops": ["rice", "maize", "cotton"]
        }

        mock_plan_crops.return_value = {
            "recommended_crops": [
                {
                    "name": "rice",
                    "confidence": 0.9,
                    "reasoning": "Rice is suitable for loam soil in kharif season with good rainfall",
                    "expected_yield": "4-5 tons/ha",
                    "duration_months": 4
                }
            ],
            "alternatives": ["maize", "cotton"],
            "risks": ["Pest pressure during monsoon"],
            "precautions": ["Use integrated pest management", "Ensure proper drainage"]
        }

        query = "I have loam soil, what crops should I plant for kharif season?"
        result = orchestrate_query(query)

        # Verify all agents were invoked
        assert "soil" in result["agents_invoked"]
        assert "weather" in result["agents_invoked"]
        assert "crop_planning" in result["agents_invoked"]

        # Verify data flow between agents
        assert result["soil_data"]["soil_type"] == "loam"
        assert result["weather_data"]["season"] == "kharif"
        assert len(result["crop_plan"]["recommended_crops"]) > 0

        # Verify LLM prompt contains all analysis
        prompt = result["llm_prompt_input"]
        assert "loam" in prompt.lower()
        assert "kharif" in prompt.lower()
        assert "rice" in prompt.lower()

    def test_agent_data_consistency(self):
        """Test that agent data structures are consistent across the pipeline."""
        from src.agents.orchestrator import orchestrate_query
        from unittest.mock import patch

        with patch('src.agents.orchestrator.analyze_soil') as mock_soil, \
             patch('src.agents.orchestrator.analyze_weather') as mock_weather, \
             patch('src.agents.orchestrator.plan_crops') as mock_plan:

            # Mock responses with consistent data
            soil_response = {
                "soil_type": "clay",
                "ph_level": 6.5,
                "health_score": 7,
                "constraints": ["Poor drainage"],
                "recommendations": ["Add organic matter"]
            }

            weather_response = {
                "season": "kharif",
                "suitability_score": 8,
                "temperature_range": {"min": 25, "max": 35},
                "rainfall_mm": 800,
                "risk_factors": [],
                "optimal_crops": ["rice", "jute"]
            }

            crop_response = {
                "recommended_crops": [{"name": "rice", "confidence": 0.8}],
                "alternatives": ["jute"],
                "risks": ["Waterlogging"],
                "precautions": ["Improve drainage"]
            }

            mock_soil.return_value = soil_response
            mock_weather.return_value = weather_response
            mock_plan.return_value = crop_response

            result = orchestrate_query("test crop planning")

            # Verify data integrity
            assert result["soil_data"] == soil_response
            assert result["weather_data"] == weather_response
            assert result["crop_plan"] == crop_response

            # Verify crop planning received correct inputs
            mock_plan.assert_called_once()
            call_args = mock_plan.call_args[0]
            assert call_args[0] == soil_response  # soil_data
            assert call_args[1] == weather_response  # weather_data