"""
Soil Agent
==========

Analyzes soil conditions using RAG over farmer dataset.
Returns structured JSON with soil health insights and constraints.

Enhanced Features:
- NPK extraction from query text
- Organic matter and micronutrient detection
- Data source tracking with confidence scoring
- Location-aware soil profiles
- Progressive fallback (PINCODE → District → State)
- SELF-LEARNING: Learns new regional soil profiles from queries and stores for future use
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from rag.retrieve import retrieve_documents
from utils.logger import logger
from utils.learning_db import (
    get_soil_profile as db_get_soil,
    save_soil_profile,
    learn_soil_from_query
)


# Regional soil profiles for fallback when no specific data available
REGIONAL_SOIL_PROFILES = {
    "punjab": {"type": "loam", "ph": 7.8, "fertility": "high", "organic_matter": 0.6},
    "maharashtra": {"type": "black_cotton", "ph": 7.5, "fertility": "medium", "organic_matter": 0.5},
    "rajasthan": {"type": "sandy", "ph": 8.2, "fertility": "low", "organic_matter": 0.3},
    "kerala": {"type": "laterite", "ph": 5.5, "fertility": "medium", "organic_matter": 0.7},
    "west_bengal": {"type": "alluvial", "ph": 6.8, "fertility": "high", "organic_matter": 0.8},
    "tamil_nadu": {"type": "red", "ph": 6.5, "fertility": "medium", "organic_matter": 0.5},
    "karnataka": {"type": "red", "ph": 6.8, "fertility": "medium", "organic_matter": 0.5},
    "uttar_pradesh": {"type": "alluvial", "ph": 7.2, "fertility": "high", "organic_matter": 0.6},
    "madhya_pradesh": {"type": "black_cotton", "ph": 7.6, "fertility": "medium", "organic_matter": 0.5},
    "gujarat": {"type": "black_cotton", "ph": 7.8, "fertility": "medium", "organic_matter": 0.4},
    "default": {"type": "loam", "ph": 7.0, "fertility": "medium", "organic_matter": 0.5}
}

# Soil type characteristics for analysis
SOIL_CHARACTERISTICS = {
    "clay": {"drainage": "poor", "water_retention": "high", "workability": "difficult", "nutrient_retention": "high"},
    "sandy": {"drainage": "excellent", "water_retention": "low", "workability": "easy", "nutrient_retention": "low"},
    "loam": {"drainage": "good", "water_retention": "moderate", "workability": "easy", "nutrient_retention": "good"},
    "silt": {"drainage": "moderate", "water_retention": "high", "workability": "moderate", "nutrient_retention": "good"},
    "peat": {"drainage": "poor", "water_retention": "very_high", "workability": "moderate", "nutrient_retention": "high"},
    "chalk": {"drainage": "excellent", "water_retention": "low", "workability": "moderate", "nutrient_retention": "low"},
    "black_cotton": {"drainage": "poor", "water_retention": "high", "workability": "difficult", "nutrient_retention": "high"},
    "red": {"drainage": "good", "water_retention": "moderate", "workability": "moderate", "nutrient_retention": "moderate"},
    "laterite": {"drainage": "excellent", "water_retention": "low", "workability": "easy", "nutrient_retention": "low"},
    "alluvial": {"drainage": "good", "water_retention": "moderate", "workability": "easy", "nutrient_retention": "high"}
}


def analyze_soil(query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Analyze soil conditions from user query using RAG.

    Args:
        query: User's text query (e.g., "my soil is clay with pH 6.5")
        context: Optional additional context including:
            - pincode: User's location pincode
            - district: District name
            - state: State name
            - previous_soil_test: Previous soil test results

    Returns:
        Structured JSON response with soil analysis including:
        - Soil parameters (type, pH, NPK, organic matter)
        - Health score with confidence
        - Constraints and recommendations
        - Data source tracking
    """
    # Ensure query is never None
    query = query or ""
    context = context or {}
    
    try:
        logger.info(f"Soil Agent analyzing: {query}")

        # Use RAG to retrieve relevant soil knowledge
        docs = retrieve_documents(f"soil analysis {query}")
        
        # Get location context for regional fallback
        location_data = _get_location_context(context)

        # Extract soil parameters from query, docs, and location
        soil_data = _extract_soil_parameters(query, docs, location_data)

        # Calculate health score and constraints
        health_score, health_confidence = _calculate_soil_health(soil_data)
        constraints = _identify_constraints(soil_data)
        recommendations = _generate_recommendations(soil_data)
        
        # Extract micronutrients if mentioned
        micronutrients = _extract_micronutrients(query, docs)

        response = {
            "soil_type": soil_data.get("type", "unknown"),
            "ph_level": soil_data.get("ph", 7.0),
            "npk_levels": {
                "nitrogen": soil_data.get("nitrogen", 0.0),
                "phosphorus": soil_data.get("phosphorus", 0.0),
                "potassium": soil_data.get("potassium", 0.0)
            },
            "organic_matter_percent": soil_data.get("organic_matter", 0.0),
            "micronutrients": micronutrients,
            "soil_characteristics": SOIL_CHARACTERISTICS.get(
                soil_data.get("type", "loam"), 
                SOIL_CHARACTERISTICS["loam"]
            ),
            "health_score": health_score,
            "health_confidence": health_confidence,
            "constraints": constraints,
            "recommendations": recommendations,
            "data_sources": soil_data.get("data_sources", []),
            "data_freshness": soil_data.get("data_freshness", "estimated"),
            "location_context": {
                "pincode": context.get("pincode"),
                "district": context.get("district"),
                "state": context.get("state"),
                "fallback_level": location_data.get("fallback_level", "default")
            }
        }

        # Self-learning: Save soil profile if we got good data from user query
        if "user_query" in soil_data.get("data_sources", []) and health_confidence >= 0.5:
            region = context.get("district") or context.get("state")
            if region and soil_data.get("type") != "unknown":
                try:
                    learn_soil_from_query(
                        region=region,
                        soil_type=soil_data.get("type"),
                        ph_level=soil_data.get("ph"),
                        characteristics={
                            "organic_matter": soil_data.get("organic_matter"),
                            "nitrogen": soil_data.get("nitrogen"),
                            "phosphorus": soil_data.get("phosphorus"),
                            "potassium": soil_data.get("potassium")
                        },
                        source="user_query_extracted"
                    )
                    logger.info(f"Learned soil profile for {region}")
                except Exception as learn_err:
                    logger.debug(f"Could not save learned soil profile: {learn_err}")

        logger.info(f"Soil Agent response: health_score={health_score}, confidence={health_confidence}")
        return response

    except Exception as e:
        logger.error(f"Soil Agent error: {e}")
        return {
            "error": str(e),
            "soil_type": "unknown",
            "ph_level": 7.0,
            "npk_levels": {"nitrogen": 0.0, "phosphorus": 0.0, "potassium": 0.0},
            "organic_matter_percent": 0.0,
            "micronutrients": {},
            "soil_characteristics": SOIL_CHARACTERISTICS["loam"],
            "health_score": 5,
            "health_confidence": 0.1,
            "constraints": ["Analysis failed - using default values"],
            "recommendations": ["Get professional soil test", "Consult local agricultural expert"],
            "data_sources": ["default_fallback"],
            "data_freshness": "unknown",
            "location_context": {"fallback_level": "error"}
        }


def _get_location_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get location-based soil profile with progressive fallback.
    Uses self-learning: checks DynamoDB for learned profiles first.
    
    Fallback order: DynamoDB Learned → State Regional → Default
    """
    location_data = {
        "fallback_level": "default",
        "confidence": 0.3
    }
    
    state = (context.get("state") or "").lower().replace(" ", "_")
    district = (context.get("district") or "").lower().replace(" ", "_")
    
    # Try learned profile from DynamoDB first (district level)
    if district:
        learned_profile = db_get_soil(district)
        if learned_profile:
            location_data.update(learned_profile)
            location_data["fallback_level"] = "learned_district"
            location_data["confidence"] = learned_profile.get("confidence", 0.75)
            logger.info(f"Using learned soil profile for district: {district}")
            return location_data
    
    # Try learned profile from DynamoDB (state level)
    if state:
        learned_profile = db_get_soil(state)
        if learned_profile:
            location_data.update(learned_profile)
            location_data["fallback_level"] = "learned_state"
            location_data["confidence"] = learned_profile.get("confidence", 0.7)
            logger.info(f"Using learned soil profile for state: {state}")
            return location_data
    
    # Try state-level data from static profiles
    if state in REGIONAL_SOIL_PROFILES:
        location_data.update(REGIONAL_SOIL_PROFILES[state])
        location_data["fallback_level"] = "state"
        location_data["confidence"] = 0.6
    else:
        location_data.update(REGIONAL_SOIL_PROFILES["default"])
    
    return location_data


def _extract_soil_parameters(query: str, docs: List[Dict], location_data: Dict) -> Dict[str, Any]:
    """Extract soil parameters from query, RAG docs, and location context."""
    query_lower = (query or "").lower()
    
    data_sources = []
    
    # === Extract Soil Type ===
    soil_types = {
        "clay": ["clay", "clayey", "heavy soil"],
        "sandy": ["sandy", "sand", "light soil"],
        "loam": ["loam", "loamy"],
        "silt": ["silt", "silty"],
        "peat": ["peat", "peaty", "organic soil"],
        "chalk": ["chalk", "chalky", "calcareous"],
        "black_cotton": ["black cotton", "black soil", "regur", "vertisol"],
        "red": ["red soil", "red earth", "alfisol"],
        "laterite": ["laterite", "lateritic"],
        "alluvial": ["alluvial", "river soil", "doab"]
    }
    
    soil_type = location_data.get("type", "unknown")
    for st, keywords in soil_types.items():
        if any(kw in query_lower for kw in keywords):
            soil_type = st
            data_sources.append("user_query")
            break
    
    if "user_query" not in data_sources and soil_type != "unknown":
        data_sources.append("location_profile")

    # === Extract pH ===
    ph = location_data.get("ph", 7.0)
    ph_patterns = [
        r'ph\s*(?:is|=|:)?\s*(\d+\.?\d*)',
        r'ph\s*level\s*(?:is|=|:)?\s*(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*ph',
        r'acidity\s*(?:is|=|:)?\s*(\d+\.?\d*)',
    ]
    
    for pattern in ph_patterns:
        ph_match = re.search(pattern, query_lower)
        if ph_match:
            extracted_ph = float(ph_match.group(1))
            if 0 <= extracted_ph <= 14:  # Valid pH range
                ph = extracted_ph
                data_sources.append("user_query_ph")
                break

    # === Extract NPK Values ===
    npk = _extract_npk_values(query_lower)
    if any(v > 0 for v in npk.values()):
        data_sources.append("user_query_npk")
    
    # === Extract Organic Matter ===
    organic_matter = location_data.get("organic_matter", 0.5)
    om_match = re.search(r'organic\s*(?:matter|content)?\s*(?:is|=|:)?\s*(\d+\.?\d*)\s*%?', query_lower)
    if om_match:
        organic_matter = float(om_match.group(1))
        if organic_matter > 10:  # Likely in wrong unit, convert
            organic_matter = organic_matter / 100
        data_sources.append("user_query_om")
    
    # Check for organic matter keywords
    if "rich organic" in query_lower or "high organic" in query_lower:
        organic_matter = max(organic_matter, 0.8)
    elif "low organic" in query_lower or "poor organic" in query_lower:
        organic_matter = min(organic_matter, 0.3)

    # Determine data freshness
    data_freshness = "estimated"
    if "user_query_ph" in data_sources or "user_query_npk" in data_sources:
        data_freshness = "user_provided"
    
    return {
        "type": soil_type,
        "ph": ph,
        "nitrogen": npk["nitrogen"],
        "phosphorus": npk["phosphorus"],
        "potassium": npk["potassium"],
        "organic_matter": organic_matter,
        "data_sources": data_sources or ["location_profile"],
        "data_freshness": data_freshness,
        "location_confidence": location_data.get("confidence", 0.3)
    }


def _extract_npk_values(query_lower: str) -> Dict[str, float]:
    """Extract NPK values from query text."""
    npk = {"nitrogen": 0.0, "phosphorus": 0.0, "potassium": 0.0}
    
    # Pattern: "N-P-K" format like "10-20-10" or "NPK 10:20:10"
    npk_ratio_match = re.search(r'(?:npk|n-p-k)?\s*(\d+)\s*[-:]\s*(\d+)\s*[-:]\s*(\d+)', query_lower)
    if npk_ratio_match:
        npk["nitrogen"] = float(npk_ratio_match.group(1))
        npk["phosphorus"] = float(npk_ratio_match.group(2))
        npk["potassium"] = float(npk_ratio_match.group(3))
        return npk
    
    # Individual nutrient patterns
    n_patterns = [
        r'nitrogen\s*(?:is|=|:)?\s*(\d+\.?\d*)',
        r'n\s*(?:is|=|:)?\s*(\d+\.?\d*)\s*(?:kg|%)',
        r'urea\s*(?:is|=|:)?\s*(\d+\.?\d*)'
    ]
    
    p_patterns = [
        r'phosphorus\s*(?:is|=|:)?\s*(\d+\.?\d*)',
        r'phosphate\s*(?:is|=|:)?\s*(\d+\.?\d*)',
        r'p\s*(?:is|=|:)?\s*(\d+\.?\d*)\s*(?:kg|%)'
    ]
    
    k_patterns = [
        r'potassium\s*(?:is|=|:)?\s*(\d+\.?\d*)',
        r'potash\s*(?:is|=|:)?\s*(\d+\.?\d*)',
        r'k\s*(?:is|=|:)?\s*(\d+\.?\d*)\s*(?:kg|%)'
    ]
    
    for pattern in n_patterns:
        match = re.search(pattern, query_lower)
        if match:
            npk["nitrogen"] = float(match.group(1))
            break
    
    for pattern in p_patterns:
        match = re.search(pattern, query_lower)
        if match:
            npk["phosphorus"] = float(match.group(1))
            break
    
    for pattern in k_patterns:
        match = re.search(pattern, query_lower)
        if match:
            npk["potassium"] = float(match.group(1))
            break
    
    # Qualitative indicators
    if "nitrogen deficient" in query_lower or "low nitrogen" in query_lower:
        npk["nitrogen"] = max(npk["nitrogen"], 10.0)  # Below optimal
    elif "high nitrogen" in query_lower or "rich nitrogen" in query_lower:
        npk["nitrogen"] = max(npk["nitrogen"], 50.0)
    
    return npk


def _extract_micronutrients(query: str, docs: List[Dict]) -> Dict[str, Any]:
    """Extract micronutrient information from query and docs."""
    query_lower = (query or "").lower()
    micronutrients = {}
    
    # Micronutrient patterns
    micro_patterns = {
        "zinc": [r'zinc\s*(?:is|=|:)?\s*(\d+\.?\d*)', r'zn\s*(?:is|=|:)?\s*(\d+\.?\d*)'],
        "iron": [r'iron\s*(?:is|=|:)?\s*(\d+\.?\d*)', r'fe\s*(?:is|=|:)?\s*(\d+\.?\d*)'],
        "manganese": [r'manganese\s*(?:is|=|:)?\s*(\d+\.?\d*)', r'mn\s*(?:is|=|:)?\s*(\d+\.?\d*)'],
        "copper": [r'copper\s*(?:is|=|:)?\s*(\d+\.?\d*)', r'cu\s*(?:is|=|:)?\s*(\d+\.?\d*)'],
        "boron": [r'boron\s*(?:is|=|:)?\s*(\d+\.?\d*)', r'b\s*(?:is|=|:)?\s*(\d+\.?\d*)\s*ppm'],
        "sulfur": [r'sulfur\s*(?:is|=|:)?\s*(\d+\.?\d*)', r'sulphur\s*(?:is|=|:)?\s*(\d+\.?\d*)']
    }
    
    for nutrient, patterns in micro_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                micronutrients[nutrient] = {
                    "value": float(match.group(1)),
                    "unit": "ppm",
                    "source": "user_query"
                }
                break
        
        # Check for deficiency indicators
        if nutrient not in micronutrients:
            if f"{nutrient} deficien" in query_lower or f"low {nutrient}" in query_lower:
                micronutrients[nutrient] = {
                    "status": "deficient",
                    "source": "user_indication"
                }
    
    return micronutrients


def _calculate_soil_health(soil_data: Dict[str, Any]) -> Tuple[int, float]:
    """
    Calculate soil health score (1-10) with confidence.
    
    Returns:
        Tuple of (health_score, confidence)
    """
    score = 5  # Base score
    confidence_factors = []
    
    soil_type = soil_data.get("type", "unknown").lower()
    ph = soil_data.get("ph", 7.0)
    organic_matter = soil_data.get("organic_matter", 0.5)
    
    # Soil type scoring
    type_scores = {
        "loam": 3, "alluvial": 3, "black_cotton": 2,
        "silt": 2, "clay": 1, "red": 1,
        "sandy": 0, "laterite": 0, "chalk": -1,
        "peat": 1, "unknown": 0
    }
    score += type_scores.get(soil_type, 0)
    confidence_factors.append(0.8 if soil_type != "unknown" else 0.4)
    
    # pH scoring (optimal 6.0-7.5)
    if 6.0 <= ph <= 7.5:
        score += 2
        confidence_factors.append(0.9)
    elif 5.5 <= ph <= 8.0:
        score += 1
        confidence_factors.append(0.75)
    elif ph < 5.0 or ph > 8.5:
        score -= 2
        confidence_factors.append(0.8)
    else:
        confidence_factors.append(0.6)
    
    # Organic matter scoring
    if organic_matter >= 0.6:
        score += 1
        confidence_factors.append(0.7)
    elif organic_matter < 0.3:
        score -= 1
        confidence_factors.append(0.6)
    
    # NPK scoring
    n = soil_data.get("nitrogen", 0)
    p = soil_data.get("phosphorus", 0)
    k = soil_data.get("potassium", 0)
    
    if n > 30 and p > 20 and k > 20:
        score += 1
        confidence_factors.append(0.85)
    elif n > 0 or p > 0 or k > 0:
        confidence_factors.append(0.7)
    
    # Clamp score to 1-10 range
    score = max(1, min(10, score))
    
    # Calculate overall confidence
    confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    return score, round(confidence, 2)


def _identify_constraints(soil_data: Dict[str, Any]) -> List[str]:
    """Identify soil constraints based on soil data."""
    constraints = []
    
    soil_type = soil_data.get("type", "unknown").lower()
    ph = soil_data.get("ph", 7.0)
    organic_matter = soil_data.get("organic_matter", 0.5)
    
    # Soil type constraints
    type_constraints = {
        "clay": ["Poor drainage - risk of waterlogging", "Difficult to work when wet"],
        "sandy": ["Low nutrient retention", "Requires frequent irrigation", "Low water holding capacity"],
        "laterite": ["Low nutrient retention", "May be acidic", "Low organic matter"],
        "chalk": ["Alkaline pH limits nutrient availability", "May cause iron chlorosis"],
        "peat": ["Poor drainage", "May be acidic", "Slow to warm in spring"]
    }
    constraints.extend(type_constraints.get(soil_type, []))
    
    # pH constraints
    if ph < 5.5:
        constraints.append(f"Acidic soil (pH {ph}) - may require liming")
    elif ph > 8.0:
        constraints.append(f"Alkaline soil (pH {ph}) - may cause micronutrient deficiency")
    
    # Organic matter constraints
    if organic_matter < 0.3:
        constraints.append("Low organic matter - add compost or green manure")
    
    # NPK constraints
    if soil_data.get("nitrogen", 0) < 20:
        constraints.append("Low nitrogen - consider nitrogen fertilization")
    if soil_data.get("phosphorus", 0) < 15:
        constraints.append("Low phosphorus - consider phosphorus supplementation")
    if soil_data.get("potassium", 0) < 15:
        constraints.append("Low potassium - consider potash application")
    
    if not constraints:
        constraints.append("No major constraints identified")
    
    return constraints


def _generate_recommendations(soil_data: Dict[str, Any]) -> List[str]:
    """Generate soil improvement recommendations."""
    recommendations = []
    
    soil_type = soil_data.get("type", "unknown").lower()
    ph = soil_data.get("ph", 7.0)
    organic_matter = soil_data.get("organic_matter", 0.5)
    
    # Soil type recommendations
    type_recommendations = {
        "clay": [
            "Add organic matter to improve drainage",
            "Use raised beds for better root development",
            "Avoid working soil when wet"
        ],
        "sandy": [
            "Add organic matter to improve water retention",
            "Use mulching to reduce water loss",
            "Apply fertilizers in split doses"
        ],
        "loam": [
            "Maintain organic matter levels with regular composting",
            "Practice crop rotation for soil health"
        ],
        "laterite": [
            "Add lime to correct acidity",
            "Regular organic matter application",
            "Micronutrient supplementation recommended"
        ],
        "black_cotton": [
            "Ensure proper drainage",
            "Add gypsum to improve soil structure",
            "Avoid waterlogging during monsoon"
        ]
    }
    recommendations.extend(type_recommendations.get(soil_type, ["Regular soil testing recommended"]))
    
    # pH recommendations
    if ph < 5.5:
        recommendations.append("Apply agricultural lime to raise pH")
    elif ph > 8.0:
        recommendations.append("Apply eleite sulfur or organic acids to lower pH")
    
    # Organic matter recommendations
    if organic_matter < 0.4:
        recommendations.append("Add farmyard manure or compost (10-15 tons/ha)")
        recommendations.append("Consider green manuring with dhaincha or sunhemp")
    
    # NPK recommendations
    n = soil_data.get("nitrogen", 0)
    p = soil_data.get("phosphorus", 0)
    k = soil_data.get("potassium", 0)
    
    if n < 20:
        recommendations.append("Apply urea or ammonium sulfate for nitrogen")
    if p < 15:
        recommendations.append("Apply DAP or single super phosphate")
    if k < 15:
        recommendations.append("Apply muriate of potash (MOP)")
    
    if not recommendations:
        recommendations.append("Soil conditions are good - maintain current practices")
    
    return recommendations