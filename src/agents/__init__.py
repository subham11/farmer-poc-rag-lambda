"""
Multi-Agent Voice Assistant
===========================

This module implements a multi-agent system for farmer queries:
- Soil Agent: Analyzes soil conditions using RAG
- Weather Agent: Analyzes weather suitability
- Crop Planning Agent: Recommends crops based on soil and weather
- Orchestrator: Coordinates agents and produces final LLM input

All agents are stateless and return structured JSON responses.

Enhanced Features (v2):
- Location-aware analysis (PINCODE → District → State fallback)
- Confidence scoring at every level
- Data source tracking and freshness indicators
- Comprehensive risk assessment
- Market price and government scheme integration
- Multi-turn context support
"""

import json
import logging
from typing import Dict, Any, List
from rag.retrieve import retrieve_documents
from utils.logger import logger

# Agent response schemas (v2 - enhanced)

SOIL_AGENT_SCHEMA = {
    "soil_type": "string",  # e.g., "clay", "sandy", "loam", "black_cotton", "alluvial"
    "ph_level": "float",    # 0-14 scale
    "npk_levels": {
        "nitrogen": "float",  # kg/ha
        "phosphorus": "float",
        "potassium": "float"
    },
    "organic_matter_percent": "float",  # 0-1 scale
    "micronutrients": {
        "zinc": {"value": "float", "unit": "string", "source": "string"},
        "iron": {"value": "float", "unit": "string", "source": "string"},
        # ... other micronutrients
    },
    "soil_characteristics": {
        "drainage": "string",  # poor, moderate, good, excellent
        "water_retention": "string",
        "workability": "string",
        "nutrient_retention": "string"
    },
    "health_score": "int",  # 1-10 scale
    "health_confidence": "float",  # 0-1 scale
    "constraints": ["string"],  # List of soil limitations with severity
    "recommendations": ["string"],  # Soil improvement suggestions with priority
    "data_sources": ["string"],  # Where data came from
    "data_freshness": "string",  # user_provided, estimated, historical
    "location_context": {
        "pincode": "string",
        "district": "string",
        "state": "string",
        "fallback_level": "string"  # pincode, district, state, default
    }
}

WEATHER_AGENT_SCHEMA = {
    "season": "string",     # e.g., "kharif", "rabi", "zaid"
    "season_dates": {
        "start": "string",
        "end": "string",
        "sowing_window": "string"
    },
    "temperature_range": {
        "min": "float",
        "max": "float",
        "optimal_range": "string"
    },
    "rainfall_mm": "float",  # Seasonal rainfall in mm
    "rainfall_pattern": "string",  # scanty, light, moderate, heavy, very_heavy
    "humidity_percent": "float",
    "suitability_score": "int",  # 1-10 for current conditions
    "suitability_confidence": "float",  # 0-1 scale
    "risk_assessment": {
        "frost": {"level": "string", "details": "string"},
        "drought": {"level": "string", "details": "string"},
        "flood": {"level": "string", "details": "string"},
        "heat_stress": {"level": "string", "details": "string"},
        "disease_pressure": {"level": "string", "details": "string"},
        "summary": ["string"]
    },
    "risk_factors": ["string"],  # Legacy field for backward compatibility
    "irrigation_needs": {
        "level": "string",
        "frequency": "string",
        "estimated_mm_per_week": "int",
        "notes": "string"
    },
    "optimal_crops": [  # Weather-suitable crops with scores
        {
            "crop": "string",
            "weather_suitability": "float",
            "factors": ["string"]
        }
    ],
    "data_sources": ["string"],
    "data_freshness": "string",
    "location_context": {
        "pincode": "string",
        "district": "string",
        "state": "string",
        "fallback_level": "string"
    }
}

CROP_PLANNING_AGENT_SCHEMA = {
    "recommended_crops": [
        {
            "name": "string",
            "confidence": "float",  # 0-1 scale
            "reasoning": "string",
            "expected_yield": {
                "kg_per_ha": "int",
                "range": "string",
                "quality_factor": "string",
                "soil_health_impact": "string"
            },
            "duration_months": "int",
            "water_requirement": "string",
            "msp_available": "bool",
            "economics": {
                "input_costs": {
                    "seeds": "float",
                    "fertilizers": "float",
                    "irrigation": "float",
                    "pesticides": "float",
                    "total": "float"
                },
                "expected_yield_kg": "float",
                "revenue_estimate": {
                    "at_market_min": "float",
                    "at_market_max": "float",
                    "at_msp": "float"
                },
                "profit_estimate": {
                    "at_market_min": "float",
                    "at_market_max": "float",
                    "at_msp": "float"
                },
                "roi_percent": "float",
                "msp_2024": "float",
                "price_per_quintal": {"min": "float", "max": "float"},
                "farm_size_ha": "float"
            },
            "varieties": [
                {
                    "name": "string",
                    "type": "string",  # high_yield, drought_resistant, etc.
                    "reason": "string"
                }
            ],
            "government_schemes": [
                {
                    "name": "string",
                    "benefit": "string",
                    "eligibility": "string"
                }
            ]
        }
    ],
    "alternatives": [
        {
            "crop": "string",
            "reason": "string",
            "type": "string"  # low_input_alternative, soil_specific, etc.
        }
    ],
    "risks": [
        {
            "type": "string",  # soil, weather, disease, market
            "severity": "string",
            "description": "string",
            "affected_crops": ["string"]
        }
    ],
    "precautions": [
        {
            "action": "string",
            "priority": "string",  # high, medium, low
            "timing": "string"  # before_sowing, land_preparation, etc.
        }
    ],
    "overall_confidence": "float",  # 0-1 scale
    "season": "string",
    "planning_factors": {
        "soil_health": "int",
        "soil_confidence": "float",
        "weather_suitability": "int",
        "weather_confidence": "float",
        "irrigation_available": "bool"
    },
    "data_sources": ["string"]
}

ORCHESTRATOR_SCHEMA = {
    "query": "string",
    "intent_analysis": {
        "agents": ["string"],
        "confidence": "float",
        "detected_intents": {
            "intent_name": {
                "score": "float",
                "matched_keywords": ["string"]
            }
        },
        "is_default_selection": "bool"
    },
    "agents_invoked": ["string"],
    "soil_data": "SOIL_AGENT_SCHEMA",
    "weather_data": "WEATHER_AGENT_SCHEMA",
    "crop_plan": "CROP_PLANNING_AGENT_SCHEMA",
    "agent_errors": [
        {
            "agent": "string",
            "error": "string"
        }
    ],
    "overall_confidence": "float",  # 0-1 scale
    "data_sources": ["string"],
    "data_freshness_summary": {
        "soil": "string",
        "weather": "string",
        "crop_economics": "string",
        "overall": "string"
    },
    "llm_prompt_input": "string"  # Structured input for LLM
}