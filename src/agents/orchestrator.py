"""
Orchestrator Agent
==================

Coordinates multi-agent system for farmer queries.
Determines which agents to invoke and aggregates their outputs.
Produces structured input for LLM generation.

Enhanced Features:
- Advanced intent analysis with confidence scoring
- Multi-turn context support for conversation continuity
- Confidence aggregation across all agents
- Data source summary and freshness tracking
- Graceful fallback handling with partial results
- Location context propagation to all agents
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from .soil_agent import analyze_soil
from .weather_agent import analyze_weather
from .crop_planning_agent import plan_crops
from utils.logger import logger


# Intent patterns for better query understanding
INTENT_PATTERNS = {
    "soil_analysis": {
        "keywords": ["soil", "ph", "clay", "sandy", "loam", "nitrogen", "phosphorus", 
                    "potassium", "npk", "fertile", "fertility", "land", "ground", 
                    "earth", "mitti", "organic matter", "micronutrient"],
        "weight": 1.0
    },
    "weather_analysis": {
        "keywords": ["weather", "rain", "rainfall", "season", "kharif", "rabi", "zaid", 
                    "temperature", "humidity", "monsoon", "winter", "summer", "climate",
                    "frost", "drought", "flood", "irrigation"],
        "weight": 1.0
    },
    "crop_planning": {
        "keywords": ["crop", "plant", "grow", "cultivate", "farm", "recommend", "suggest",
                    "what to plant", "which crop", "best crop", "sow", "harvest", "yield",
                    "variety", "seed", "profit", "income", "msp", "price"],
        "weight": 1.2  # Higher weight as this is often the ultimate goal
    },
    "market_info": {
        "keywords": ["price", "msp", "market", "sell", "income", "profit", "cost",
                    "mandi", "procurement", "subsidy", "scheme", "loan"],
        "weight": 0.8
    },
    "pest_disease": {
        "keywords": ["pest", "disease", "insect", "fungus", "virus", "blight", "rot",
                    "spray", "pesticide", "medicine", "treatment"],
        "weight": 0.9
    }
}


def orchestrate_query(query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Orchestrate multi-agent analysis for farmer query.

    Args:
        query: User's text query from ASR
        context: Optional additional context including:
            - pincode: User's location pincode
            - district: District name
            - state: State name
            - language: User's language preference
            - previous_queries: List of previous queries in session
            - user_profile: User's farm details if available
            - conversation_id: For multi-turn tracking

    Returns:
        Structured response with agent outputs, confidence scores, and LLM input
    """
    context = context or {}
    
    try:
        logger.info(f"Orchestrator processing query: {query}")

        # Analyze query intent with confidence scoring
        intent_analysis = _analyze_query_intent(query, context)
        agents_to_invoke = intent_analysis["agents"]
        intent_confidence = intent_analysis["confidence"]

        logger.info(f"Intent analysis: agents={agents_to_invoke}, confidence={intent_confidence}")

        # Initialize response structure
        response = {
            "query": query,
            "intent_analysis": intent_analysis,
            "agents_invoked": agents_to_invoke,
            "soil_data": None,
            "weather_data": None,
            "crop_plan": None,
            "agent_errors": [],
            "overall_confidence": 0.0,
            "data_sources": [],
            "data_freshness_summary": {},
            "llm_prompt_input": ""
        }

        # Propagate location context to all agents
        agent_context = _prepare_agent_context(context)

        # Invoke agents with error handling
        if "soil" in agents_to_invoke:
            try:
                response["soil_data"] = analyze_soil(query, agent_context)
                response["data_sources"].extend(response["soil_data"].get("data_sources", []))
            except Exception as e:
                logger.error(f"Soil Agent failed: {e}")
                response["agent_errors"].append({"agent": "soil", "error": str(e)})

        if "weather" in agents_to_invoke:
            try:
                response["weather_data"] = analyze_weather(query, agent_context)
                response["data_sources"].extend(response["weather_data"].get("data_sources", []))
            except Exception as e:
                logger.error(f"Weather Agent failed: {e}")
                response["agent_errors"].append({"agent": "weather", "error": str(e)})

        # Crop planning requires both soil and weather data
        if "crop_planning" in agents_to_invoke:
            soil_data = response["soil_data"] or _get_default_soil_data()
            weather_data = response["weather_data"] or _get_default_weather_data()
            
            try:
                response["crop_plan"] = plan_crops(
                    soil_data,
                    weather_data,
                    query,
                    agent_context
                )
                response["data_sources"].extend(response["crop_plan"].get("data_sources", []))
            except Exception as e:
                logger.error(f"Crop Planning Agent failed: {e}")
                response["agent_errors"].append({"agent": "crop_planning", "error": str(e)})

        # Calculate overall confidence
        response["overall_confidence"] = _calculate_overall_confidence(response)
        
        # Summarize data freshness
        response["data_freshness_summary"] = _summarize_data_freshness(response)
        
        # Remove duplicates from data sources
        response["data_sources"] = list(set(response["data_sources"]))

        # Generate structured LLM input
        response["llm_prompt_input"] = _generate_llm_prompt(response, context)

        logger.info(f"Orchestrator completed. Confidence: {response['overall_confidence']}")
        return response

    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        return {
            "query": query,
            "error": str(e),
            "agents_invoked": [],
            "agent_errors": [{"agent": "orchestrator", "error": str(e)}],
            "overall_confidence": 0.0,
            "llm_prompt_input": f"Error processing query: {query}. Please provide general farming advice for the user's question."
        }


def _prepare_agent_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare context to be passed to all agents."""
    return {
        "pincode": context.get("pincode"),
        "district": context.get("district"),
        "state": context.get("state"),
        "language": context.get("language", "en"),
        "farm_size_ha": context.get("user_profile", {}).get("farm_size_ha", 1.0),
        "irrigation_available": context.get("user_profile", {}).get("irrigation_available", True),
        "previous_crop": context.get("user_profile", {}).get("previous_crop"),
        "budget": context.get("user_profile", {}).get("budget")
    }


def _get_default_soil_data() -> Dict[str, Any]:
    """Get default soil data when Soil Agent fails."""
    return {
        "soil_type": "loam",
        "ph_level": 7.0,
        "npk_levels": {"nitrogen": 0.0, "phosphorus": 0.0, "potassium": 0.0},
        "health_score": 5,
        "health_confidence": 0.2,
        "constraints": ["Using default values - soil analysis unavailable"],
        "recommendations": ["Get soil tested for accurate recommendations"],
        "data_sources": ["default_fallback"]
    }


def _get_default_weather_data() -> Dict[str, Any]:
    """Get default weather data when Weather Agent fails."""
    return {
        "season": "kharif",
        "temperature_range": {"min": 22, "max": 35},
        "rainfall_mm": 800,
        "humidity_percent": 70,
        "suitability_score": 5,
        "suitability_confidence": 0.2,
        "risk_factors": ["Using default values - weather analysis unavailable"],
        "optimal_crops": [],
        "data_sources": ["default_fallback"]
    }


def _analyze_query_intent(query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Analyze query to determine which agents to invoke with confidence scoring.

    Returns:
        Dict with agents list, confidence score, and detected intents
    """
    context = context or {}
    query_lower = query.lower()
    
    detected_intents = {}
    
    # Score each intent pattern
    for intent_name, pattern in INTENT_PATTERNS.items():
        score = 0
        matched_keywords = []
        for keyword in pattern["keywords"]:
            if keyword in query_lower:
                score += 1
                matched_keywords.append(keyword)
        
        if score > 0:
            weighted_score = score * pattern["weight"]
            detected_intents[intent_name] = {
                "score": weighted_score,
                "matched_keywords": matched_keywords
            }
    
    # Determine agents to invoke
    agents = []
    
    # Check for explicit intents
    if "soil_analysis" in detected_intents:
        agents.append("soil")
    
    if "weather_analysis" in detected_intents:
        agents.append("weather")
    
    if "crop_planning" in detected_intents or "market_info" in detected_intents:
        agents.append("crop_planning")
        # Crop planning needs soil and weather context
        if "soil" not in agents:
            agents.append("soil")
        if "weather" not in agents:
            agents.append("weather")
    
    # Use previous context to inform agent selection
    previous_queries = context.get("previous_queries", [])
    if previous_queries:
        # If user previously discussed soil, continue that context
        recent_query = previous_queries[-1] if previous_queries else ""
        if "soil" in recent_query.lower() and "soil" not in agents:
            agents.append("soil")
        if any(s in recent_query.lower() for s in ["season", "weather", "kharif", "rabi"]):
            if "weather" not in agents:
                agents.append("weather")
    
    # Default: invoke all agents for comprehensive analysis
    if not agents:
        agents = ["soil", "weather", "crop_planning"]
    
    # Calculate intent confidence
    total_score = sum(d["score"] for d in detected_intents.values()) if detected_intents else 0
    max_possible = len(query.split()) * 0.5  # Rough estimate
    confidence = min(1.0, total_score / max_possible) if max_possible > 0 else 0.5
    
    # Boost confidence if explicit intent keywords found
    if detected_intents:
        confidence = max(0.6, confidence)
    
    return {
        "agents": list(set(agents)),  # Remove duplicates
        "confidence": round(confidence, 2),
        "detected_intents": detected_intents,
        "is_default_selection": len(detected_intents) == 0
    }


def _calculate_overall_confidence(response: Dict[str, Any]) -> float:
    """Calculate overall confidence from all agent responses."""
    confidences = []
    weights = []
    
    if response.get("soil_data"):
        soil_conf = response["soil_data"].get("health_confidence", 0.5)
        confidences.append(soil_conf)
        weights.append(0.25)
    
    if response.get("weather_data"):
        weather_conf = response["weather_data"].get("suitability_confidence", 0.5)
        confidences.append(weather_conf)
        weights.append(0.25)
    
    if response.get("crop_plan"):
        crop_conf = response["crop_plan"].get("overall_confidence", 0.5)
        confidences.append(crop_conf)
        weights.append(0.35)
    
    # Intent confidence
    intent_conf = response.get("intent_analysis", {}).get("confidence", 0.5)
    confidences.append(intent_conf)
    weights.append(0.15)
    
    # Penalize for errors
    error_count = len(response.get("agent_errors", []))
    error_penalty = 0.1 * error_count
    
    if confidences and weights:
        weighted_sum = sum(c * w for c, w in zip(confidences, weights))
        total_weight = sum(weights)
        overall = (weighted_sum / total_weight) - error_penalty
        return round(max(0.1, min(1.0, overall)), 2)
    
    return 0.3


def _summarize_data_freshness(response: Dict[str, Any]) -> Dict[str, str]:
    """Summarize data freshness across all agents."""
    freshness = {}
    
    if response.get("soil_data"):
        freshness["soil"] = response["soil_data"].get("data_freshness", "unknown")
    
    if response.get("weather_data"):
        freshness["weather"] = response["weather_data"].get("data_freshness", "unknown")
    
    if response.get("crop_plan"):
        freshness["crop_economics"] = "2024_msp_data"
    
    # Overall assessment
    if all(f in ["user_provided", "live"] for f in freshness.values()):
        freshness["overall"] = "high_accuracy"
    elif any(f == "historical" for f in freshness.values()):
        freshness["overall"] = "estimated_from_historical"
    else:
        freshness["overall"] = "mixed_sources"
    
    return freshness


def _generate_llm_prompt(orchestrator_response: Dict[str, Any], context: Dict[str, Any] = None) -> str:
    """
    Generate structured prompt for LLM based on agent outputs.

    This creates a comprehensive context for the LLM to generate
    a natural language response to the farmer.
    """
    context = context or {}
    query = orchestrator_response.get("query", "")
    soil_data = orchestrator_response.get("soil_data")
    weather_data = orchestrator_response.get("weather_data")
    crop_plan = orchestrator_response.get("crop_plan")
    overall_confidence = orchestrator_response.get("overall_confidence", 0.5)
    
    # Get language preference
    language = context.get("language", "en")

    prompt_parts = [
        f"User Query: {query}",
        f"Response Confidence: {overall_confidence * 100:.0f}%",
        ""
    ]
    
    # Add location context if available
    location_parts = []
    if context.get("state"):
        location_parts.append(f"State: {context['state']}")
    if context.get("district"):
        location_parts.append(f"District: {context['district']}")
    if location_parts:
        prompt_parts.append(f"Location: {', '.join(location_parts)}")
        prompt_parts.append("")

    prompt_parts.append("Analysis Results:")
    prompt_parts.append("=" * 40)

    if soil_data and not soil_data.get("error"):
        prompt_parts.extend([
            "",
            "SOIL ANALYSIS:",
            f"- Soil Type: {soil_data.get('soil_type', 'Unknown')}",
            f"- pH Level: {soil_data.get('ph_level', 'Unknown')}",
            f"- Health Score: {soil_data.get('health_score', 'Unknown')}/10 (Confidence: {soil_data.get('health_confidence', 0)*100:.0f}%)"
        ])
        
        # Add NPK if available
        npk = soil_data.get("npk_levels", {})
        if any(v > 0 for v in npk.values()):
            prompt_parts.append(f"- NPK Levels: N={npk.get('nitrogen', 0)}, P={npk.get('phosphorus', 0)}, K={npk.get('potassium', 0)}")
        
        # Add organic matter if available
        om = soil_data.get("organic_matter_percent", 0)
        if om > 0:
            prompt_parts.append(f"- Organic Matter: {om}%")
        
        constraints = soil_data.get('constraints', [])
        if constraints:
            prompt_parts.append(f"- Constraints: {'; '.join(constraints[:3])}")
        
        recommendations = soil_data.get('recommendations', [])
        if recommendations:
            prompt_parts.append(f"- Soil Recommendations: {'; '.join(recommendations[:3])}")
        
        prompt_parts.append("")

    if weather_data and not weather_data.get("error"):
        temp_range = weather_data.get('temperature_range', {})
        prompt_parts.extend([
            "WEATHER ANALYSIS:",
            f"- Season: {weather_data.get('season', 'Unknown')}",
            f"- Temperature: {temp_range.get('min', 'Unknown')}°C - {temp_range.get('max', 'Unknown')}°C",
            f"- Expected Rainfall: {weather_data.get('rainfall_mm', 'Unknown')}mm",
            f"- Humidity: {weather_data.get('humidity_percent', 'Unknown')}%",
            f"- Suitability Score: {weather_data.get('suitability_score', 'Unknown')}/10"
        ])
        
        # Add irrigation needs
        irrigation = weather_data.get('irrigation_needs', {})
        if irrigation:
            prompt_parts.append(f"- Irrigation Needs: {irrigation.get('level', 'moderate')} ({irrigation.get('notes', '')})")
        
        # Add risk factors
        risk_factors = weather_data.get('risk_factors', [])
        if risk_factors:
            prompt_parts.append(f"- Weather Risks: {'; '.join(risk_factors[:3])}")
        
        prompt_parts.append("")

    if crop_plan and not crop_plan.get("error"):
        prompt_parts.append("CROP RECOMMENDATIONS:")
        for i, crop in enumerate(crop_plan.get("recommended_crops", []), 1):
            prompt_parts.extend([
                f"",
                f"{i}. {crop.get('name', 'Unknown').upper()}:",
                f"   - Confidence: {crop.get('confidence', 0) * 100:.0f}%",
                f"   - Reasoning: {crop.get('reasoning', 'Unknown')}"
            ])
            
            # Add yield info
            yield_info = crop.get('expected_yield', {})
            if isinstance(yield_info, dict):
                prompt_parts.append(f"   - Expected Yield: {yield_info.get('range', 'Unknown')}")
            else:
                prompt_parts.append(f"   - Expected Yield: {yield_info}")
            
            prompt_parts.append(f"   - Duration: {crop.get('duration_months', 'Unknown')} months")
            
            # Add economics if available
            economics = crop.get('economics', {})
            if economics and not economics.get("error"):
                total_cost = economics.get('input_costs', {}).get('total', 0)
                msp = economics.get('msp_2024')
                if total_cost:
                    prompt_parts.append(f"   - Estimated Input Cost: ₹{total_cost:,.0f}/ha")
                if msp:
                    prompt_parts.append(f"   - MSP 2024: ₹{msp}/quintal")
            
            # Add varieties if available
            varieties = crop.get('varieties', [])
            if varieties:
                var_names = [v.get('name', '') for v in varieties[:2]]
                prompt_parts.append(f"   - Recommended Varieties: {', '.join(var_names)}")
            
            # Add schemes if available
            schemes = crop.get('government_schemes', [])
            if schemes:
                scheme_names = [s.get('name', s) if isinstance(s, dict) else s for s in schemes[:2]]
                prompt_parts.append(f"   - Applicable Schemes: {', '.join(scheme_names)}")

        # Add alternatives
        alternatives = crop_plan.get("alternatives", [])
        if alternatives:
            alt_names = []
            for alt in alternatives[:3]:
                if isinstance(alt, dict):
                    alt_names.append(f"{alt.get('crop', '')} ({alt.get('reason', '')})")
                else:
                    alt_names.append(alt)
            prompt_parts.append(f"\nAlternative Crops: {'; '.join(alt_names)}")

        # Add risks and precautions
        risks = crop_plan.get("risks", [])
        if risks:
            risk_text = []
            for r in risks[:3]:
                if isinstance(r, dict):
                    risk_text.append(f"{r.get('type', '')}: {r.get('description', '')}")
                else:
                    risk_text.append(r)
            prompt_parts.append(f"\nKey Risks: {'; '.join(risk_text)}")
        
        precautions = crop_plan.get("precautions", [])
        if precautions:
            prec_text = []
            for p in precautions[:4]:
                if isinstance(p, dict):
                    prec_text.append(f"{p.get('action', '')} [{p.get('priority', '')}]")
                else:
                    prec_text.append(p)
            prompt_parts.append(f"\nPrecautions: {'; '.join(prec_text)}")

    # Add data confidence note
    prompt_parts.extend([
        "",
        "=" * 40,
        f"Data Confidence: {overall_confidence * 100:.0f}%",
        f"Data Sources: {', '.join(orchestrator_response.get('data_sources', ['unknown'])[:5])}"
    ])
    
    # Add any errors
    errors = orchestrator_response.get("agent_errors", [])
    if errors:
        prompt_parts.append(f"\nNote: Some analyses incomplete due to: {', '.join(e.get('agent', '') for e in errors)}")

    # Add instructions for LLM
    prompt_parts.extend([
        "",
        "=" * 40,
        "Instructions for Response:",
        "- Provide a helpful, natural response to the farmer",
        "- Focus on practical, actionable farming advice",
        "- Explain technical terms in simple language",
        "- Include specific recommendations based on the analysis",
        "- Mention government schemes if applicable",
        "- Include any risks and how to mitigate them",
        f"- If confidence is below 50%, mention that recommendations are estimates",
        "- Keep response concise but comprehensive (2-3 paragraphs)",
        "",
        "Response:"
    ])

    return "\n".join(prompt_parts)