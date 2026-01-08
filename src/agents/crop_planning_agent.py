"""
Crop Planning Agent
===================

Combines soil and weather data to recommend crops.
Uses RAG and reasoning to provide crop recommendations with risks and precautions.

Enhanced Features:
- Market price awareness with seasonal trends
- Input cost estimation (seeds, fertilizers, irrigation)
- Government scheme hints and subsidies
- Variety recommendations (high-yield, drought-resistant, etc.)
- Confidence aggregation from soil and weather data
- ROI estimation and risk-adjusted recommendations
"""

import json
from typing import Dict, Any, List, Tuple, Optional
from rag.retrieve import retrieve_documents
from utils.logger import logger


# Crop database with detailed information
CROP_DATABASE = {
    "rice": {
        "varieties": {
            "high_yield": ["Pusa Basmati 1121", "IR-64", "Swarna"],
            "drought_resistant": ["Sahbhagi Dhan", "DRR 44"],
            "short_duration": ["Pusa 44", "PR 126"]
        },
        "input_costs": {"seeds": 1500, "fertilizers": 8000, "irrigation": 15000, "pesticides": 3000},
        "expected_yield_kg_ha": 4500,
        "market_price_range": {"min": 2000, "max": 2200},  # Per quintal
        "msp_2024": 2300,  # Minimum Support Price
        "suitable_soil": ["clay", "loam", "alluvial"],
        "water_requirement": "high",
        "government_schemes": ["PM-KISAN", "PMFBY", "Paddy Procurement at MSP"]
    },
    "wheat": {
        "varieties": {
            "high_yield": ["HD 3086", "PBW 725", "WH 1105"],
            "drought_resistant": ["HD 2987", "Raj 4120"],
            "disease_resistant": ["HD 3226", "DBW 187"]
        },
        "input_costs": {"seeds": 2000, "fertilizers": 6000, "irrigation": 8000, "pesticides": 2000},
        "expected_yield_kg_ha": 4000,
        "market_price_range": {"min": 2100, "max": 2400},
        "msp_2024": 2275,
        "suitable_soil": ["loam", "clay", "alluvial"],
        "water_requirement": "moderate",
        "government_schemes": ["PM-KISAN", "PMFBY", "Wheat Procurement"]
    },
    "maize": {
        "varieties": {
            "high_yield": ["HQPM 1", "Vivek QPM 9", "DHM 117"],
            "drought_resistant": ["PEHM 5", "Vivek 27"],
            "short_duration": ["HQPM 5", "Vivek 21"]
        },
        "input_costs": {"seeds": 2500, "fertilizers": 5000, "irrigation": 6000, "pesticides": 2500},
        "expected_yield_kg_ha": 5000,
        "market_price_range": {"min": 1800, "max": 2100},
        "msp_2024": 2090,
        "suitable_soil": ["loam", "sandy", "alluvial"],
        "water_requirement": "moderate",
        "government_schemes": ["PM-KISAN", "PMFBY", "e-NAM"]
    },
    "cotton": {
        "varieties": {
            "high_yield": ["RCH 2 BG II", "Bunny BG II", "Mallika BG II"],
            "drought_resistant": ["CICR 2", "Suraj"],
            "pest_resistant": ["Bt Cotton varieties"]
        },
        "input_costs": {"seeds": 4000, "fertilizers": 8000, "irrigation": 10000, "pesticides": 6000},
        "expected_yield_kg_ha": 2000,
        "market_price_range": {"min": 6000, "max": 7000},
        "msp_2024": 7020,  # Long staple
        "suitable_soil": ["black_cotton", "loam"],
        "water_requirement": "moderate",
        "government_schemes": ["PM-KISAN", "PMFBY", "Cotton Corporation of India Procurement"]
    },
    "soybean": {
        "varieties": {
            "high_yield": ["JS 9560", "JS 20-34", "NRC 142"],
            "drought_resistant": ["NRC 86", "JS 335"],
            "disease_resistant": ["MACS 1407", "NRC 150"]
        },
        "input_costs": {"seeds": 3000, "fertilizers": 4000, "irrigation": 4000, "pesticides": 2000},
        "expected_yield_kg_ha": 2200,
        "market_price_range": {"min": 4000, "max": 4500},
        "msp_2024": 4600,
        "suitable_soil": ["loam", "black_cotton", "alluvial"],
        "water_requirement": "moderate",
        "government_schemes": ["PM-KISAN", "PMFBY", "NAFED Procurement"]
    },
    "groundnut": {
        "varieties": {
            "high_yield": ["TG 37A", "TAG 24", "GPBD 4"],
            "drought_resistant": ["ICGV 91114", "TG 26"],
            "high_oil": ["Girnar 3", "GJG 9"]
        },
        "input_costs": {"seeds": 4000, "fertilizers": 5000, "irrigation": 5000, "pesticides": 2000},
        "expected_yield_kg_ha": 2000,
        "market_price_range": {"min": 5000, "max": 5800},
        "msp_2024": 6377,
        "suitable_soil": ["sandy", "loam", "red"],
        "water_requirement": "low",
        "government_schemes": ["PM-KISAN", "PMFBY", "NAFED Procurement"]
    },
    "chickpea": {
        "varieties": {
            "high_yield": ["JG 14", "Vijay", "JAKI 9218"],
            "drought_resistant": ["JG 11", "Digvijay"],
            "disease_resistant": ["NBeG 47", "GNG 2144"]
        },
        "input_costs": {"seeds": 3000, "fertilizers": 3000, "irrigation": 2000, "pesticides": 1500},
        "expected_yield_kg_ha": 1800,
        "market_price_range": {"min": 4500, "max": 5500},
        "msp_2024": 5440,
        "suitable_soil": ["loam", "black_cotton", "clay"],
        "water_requirement": "low",
        "government_schemes": ["PM-KISAN", "PMFBY", "Pulses Procurement"]
    },
    "mustard": {
        "varieties": {
            "high_yield": ["Pusa Bold", "RH 749", "NRCDR 601"],
            "drought_resistant": ["NRCHB 101", "Kranti"],
            "early_maturing": ["Pusa Vijay", "RGN 229"]
        },
        "input_costs": {"seeds": 1000, "fertilizers": 4000, "irrigation": 3000, "pesticides": 1500},
        "expected_yield_kg_ha": 1500,
        "market_price_range": {"min": 5000, "max": 5800},
        "msp_2024": 5650,
        "suitable_soil": ["loam", "sandy", "alluvial"],
        "water_requirement": "low",
        "government_schemes": ["PM-KISAN", "PMFBY", "NAFED Procurement"]
    },
    "sugarcane": {
        "varieties": {
            "high_yield": ["Co 0238", "CoJ 85", "CoLK 94184"],
            "drought_resistant": ["Co 94012", "CoS 97261"],
            "high_sugar": ["Co 0118", "CoM 0265"]
        },
        "input_costs": {"seeds": 8000, "fertilizers": 12000, "irrigation": 20000, "pesticides": 4000},
        "expected_yield_kg_ha": 70000,
        "market_price_range": {"min": 300, "max": 400},  # FRP based
        "msp_2024": 315,  # Fair & Remunerative Price per quintal
        "suitable_soil": ["loam", "clay", "alluvial", "black_cotton"],
        "water_requirement": "very_high",
        "government_schemes": ["PM-KISAN", "Sugar Development Fund"]
    },
    "potato": {
        "varieties": {
            "high_yield": ["Kufri Jyoti", "Kufri Pukhraj", "Kufri Badshah"],
            "processing": ["Kufri Chipsona 1", "Kufri Frysona"],
            "disease_resistant": ["Kufri Khyati", "Kufri Himalini"]
        },
        "input_costs": {"seeds": 25000, "fertilizers": 8000, "irrigation": 6000, "pesticides": 4000},
        "expected_yield_kg_ha": 25000,
        "market_price_range": {"min": 800, "max": 1500},
        "msp_2024": None,  # No MSP for potato
        "suitable_soil": ["loam", "sandy", "alluvial"],
        "water_requirement": "moderate",
        "government_schemes": ["PM-KISAN", "PMFBY", "Cold Storage Subsidy"]
    }
}


def plan_crops(soil_data: Dict, weather_data: Dict, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Plan crop recommendations based on soil and weather analysis.

    Args:
        soil_data: Output from Soil Agent
        weather_data: Output from Weather Agent
        query: Original user query for context
        context: Optional additional context including:
            - farm_size_ha: Farm size in hectares
            - budget: Available budget
            - irrigation_available: Boolean
            - previous_crop: Last season's crop
            - preferred_crops: User's crop preferences

    Returns:
        Structured JSON response with crop recommendations including:
        - Detailed crop recommendations with varieties
        - Economics (costs, revenue, ROI)
        - Government scheme information
        - Risk assessment and mitigation
    """
    context = context or {}
    
    try:
        soil_health = soil_data.get("health_score", 5)
        soil_confidence = soil_data.get("health_confidence", 0.5)
        weather_suitability = weather_data.get("suitability_score", 5)
        weather_confidence = weather_data.get("suitability_confidence", 0.5)
        
        logger.info(f"Crop Planning Agent: soil={soil_health}({soil_confidence}), weather={weather_suitability}({weather_confidence})")

        # Use RAG to find relevant crop knowledge
        soil_type = soil_data.get("soil_type", "unknown")
        ph_level = soil_data.get("ph_level", 7.0)
        season = weather_data.get("season", "kharif")
        
        rag_query = f"crop recommendations for {soil_type} soil pH {ph_level} in {season} season"
        docs = retrieve_documents(rag_query)

        # Generate crop recommendations with enhanced analysis
        recommendations = _generate_crop_recommendations(soil_data, weather_data, docs, context)
        
        # Calculate economics for each recommendation
        for rec in recommendations:
            rec["economics"] = _calculate_crop_economics(rec["name"], context)
            rec["varieties"] = _get_variety_recommendations(rec["name"], soil_data, weather_data)
            rec["government_schemes"] = _get_applicable_schemes(rec["name"])

        # Identify alternatives and risks
        alternatives = _find_alternatives(recommendations, soil_data, weather_data)
        risks = _assess_risks(soil_data, weather_data, recommendations)
        precautions = _suggest_precautions(risks, weather_data)
        
        # Calculate overall confidence
        overall_confidence = _aggregate_confidence(soil_confidence, weather_confidence, recommendations)

        response = {
            "recommended_crops": recommendations,
            "alternatives": alternatives,
            "risks": risks,
            "precautions": precautions,
            "overall_confidence": overall_confidence,
            "season": season,
            "planning_factors": {
                "soil_health": soil_health,
                "soil_confidence": soil_confidence,
                "weather_suitability": weather_suitability,
                "weather_confidence": weather_confidence,
                "irrigation_available": context.get("irrigation_available", True)
            },
            "data_sources": ["rag_knowledge", "crop_database", "government_msp"]
        }

        logger.info(f"Crop Planning Agent: {len(recommendations)} crops recommended, confidence={overall_confidence}")
        return response

    except Exception as e:
        logger.error(f"Crop Planning Agent error: {e}")
        return {
            "error": str(e),
            "recommended_crops": [],
            "alternatives": ["Consult local agricultural expert", "Contact KVK (Krishi Vigyan Kendra)"],
            "risks": ["Unable to assess risks - analysis incomplete"],
            "precautions": ["Seek professional advice before planting"],
            "overall_confidence": 0.1,
            "data_sources": ["error_fallback"]
        }


def _aggregate_confidence(soil_confidence: float, weather_confidence: float, recommendations: List[Dict]) -> float:
    """Aggregate confidence scores from all sources."""
    crop_confidences = [r.get("confidence", 0.5) for r in recommendations]
    avg_crop_confidence = sum(crop_confidences) / len(crop_confidences) if crop_confidences else 0.5
    
    # Weighted average: soil 30%, weather 30%, crop matching 40%
    overall = 0.3 * soil_confidence + 0.3 * weather_confidence + 0.4 * avg_crop_confidence
    return round(overall, 2)


def _generate_crop_recommendations(soil_data: Dict, weather_data: Dict, docs: List[Dict], context: Dict = None) -> List[Dict]:
    """Generate crop recommendations based on soil, weather, and user context."""
    context = context or {}
    recommendations = []

    soil_type = soil_data.get("soil_type", "unknown")
    soil_health = soil_data.get("health_score", 5)
    season = weather_data.get("season", "kharif")
    weather_suitable_crops = weather_data.get("optimal_crops", [])
    irrigation_available = context.get("irrigation_available", True)
    
    # Get weather-suitable crop names
    weather_crop_names = []
    if weather_suitable_crops:
        for crop_info in weather_suitable_crops:
            if isinstance(crop_info, dict):
                weather_crop_names.append(crop_info.get("crop", ""))
            else:
                weather_crop_names.append(crop_info)

    # Filter crops suitable for soil type
    suitable_crops = []
    for crop_name, crop_info in CROP_DATABASE.items():
        if soil_type in crop_info.get("suitable_soil", []) or soil_type == "unknown":
            # Check water requirement vs irrigation availability
            water_req = crop_info.get("water_requirement", "moderate")
            if water_req in ["very_high", "high"] and not irrigation_available:
                continue
            suitable_crops.append(crop_name)

    # Cross-reference with weather-suitable crops
    if weather_crop_names:
        prioritized_crops = [c for c in suitable_crops if c in weather_crop_names]
        remaining_crops = [c for c in suitable_crops if c not in weather_crop_names]
        suitable_crops = prioritized_crops + remaining_crops[:3]

    # Generate detailed recommendations
    for crop in suitable_crops[:5]:  # Top 5
        if crop not in CROP_DATABASE:
            continue
            
        crop_info = CROP_DATABASE[crop]
        confidence = _calculate_confidence(crop, soil_data, weather_data)
        reasoning = _generate_reasoning(crop, soil_data, weather_data, crop_info)
        yield_info = _estimate_yield(crop, soil_health, crop_info)
        duration = _get_crop_duration(crop, season)

        recommendations.append({
            "name": crop,
            "confidence": confidence,
            "reasoning": reasoning,
            "expected_yield": yield_info,
            "duration_months": duration,
            "water_requirement": crop_info.get("water_requirement", "moderate"),
            "msp_available": crop_info.get("msp_2024") is not None
        })

    # Sort by confidence
    recommendations.sort(key=lambda x: x["confidence"], reverse=True)
    return recommendations[:4]  # Return top 4


def _calculate_crop_economics(crop: str, context: Dict = None) -> Dict[str, Any]:
    """Calculate detailed economics for a crop."""
    context = context or {}
    farm_size = context.get("farm_size_ha", 1.0)
    
    if crop not in CROP_DATABASE:
        return {"error": "Crop data not available"}
    
    crop_info = CROP_DATABASE[crop]
    
    # Input costs
    input_costs = crop_info.get("input_costs", {})
    total_input_cost = sum(input_costs.values()) * farm_size
    
    # Revenue estimation
    expected_yield = crop_info.get("expected_yield_kg_ha", 2000) * farm_size
    price_range = crop_info.get("market_price_range", {"min": 1500, "max": 2000})
    msp = crop_info.get("msp_2024")
    
    # Calculate at different price points
    min_revenue = (expected_yield / 100) * price_range["min"]  # Convert to quintals
    max_revenue = (expected_yield / 100) * price_range["max"]
    msp_revenue = (expected_yield / 100) * msp if msp else None
    
    # ROI calculations
    min_profit = min_revenue - total_input_cost
    max_profit = max_revenue - total_input_cost
    msp_profit = msp_revenue - total_input_cost if msp_revenue else None
    
    return {
        "input_costs": {
            "seeds": input_costs.get("seeds", 0) * farm_size,
            "fertilizers": input_costs.get("fertilizers", 0) * farm_size,
            "irrigation": input_costs.get("irrigation", 0) * farm_size,
            "pesticides": input_costs.get("pesticides", 0) * farm_size,
            "total": total_input_cost
        },
        "expected_yield_kg": expected_yield,
        "revenue_estimate": {
            "at_market_min": min_revenue,
            "at_market_max": max_revenue,
            "at_msp": msp_revenue
        },
        "profit_estimate": {
            "at_market_min": min_profit,
            "at_market_max": max_profit,
            "at_msp": msp_profit
        },
        "roi_percent": round((max_profit / total_input_cost) * 100, 1) if total_input_cost > 0 else 0,
        "msp_2024": msp,
        "price_per_quintal": price_range,
        "farm_size_ha": farm_size
    }


def _get_variety_recommendations(crop: str, soil_data: Dict, weather_data: Dict) -> List[Dict]:
    """Get variety recommendations based on conditions."""
    if crop not in CROP_DATABASE:
        return []
    
    crop_info = CROP_DATABASE[crop]
    varieties = crop_info.get("varieties", {})
    recommendations = []
    
    # Check conditions to prioritize varieties
    drought_risk = weather_data.get("risk_assessment", {}).get("drought", {}).get("level", "none")
    frost_risk = weather_data.get("risk_assessment", {}).get("frost", {}).get("level", "none")
    soil_health = soil_data.get("health_score", 5)
    
    # Prioritize based on conditions
    if drought_risk in ["moderate", "high"]:
        for v in varieties.get("drought_resistant", [])[:2]:
            recommendations.append({"name": v, "type": "drought_resistant", "reason": "Recommended due to low rainfall risk"})
    
    if frost_risk in ["moderate", "high"]:
        # Prioritize early maturing varieties
        for v in varieties.get("short_duration", varieties.get("early_maturing", []))[:2]:
            recommendations.append({"name": v, "type": "short_duration", "reason": "Early harvest before frost"})
    
    if soil_health >= 7:
        # Good soil - can go for high yield varieties
        for v in varieties.get("high_yield", [])[:2]:
            recommendations.append({"name": v, "type": "high_yield", "reason": "Good soil supports high-yield variety"})
    else:
        # Average soil - balance between yield and resilience
        for v in varieties.get("disease_resistant", varieties.get("drought_resistant", []))[:2]:
            recommendations.append({"name": v, "type": "resilient", "reason": "Better suited for challenging conditions"})
    
    # Always include at least one high-yield option
    if not any(r["type"] == "high_yield" for r in recommendations):
        for v in varieties.get("high_yield", [])[:1]:
            recommendations.append({"name": v, "type": "high_yield", "reason": "High yield potential"})
    
    return recommendations[:4]  # Return top 4 varieties


def _get_applicable_schemes(crop: str) -> List[Dict]:
    """Get government schemes applicable to the crop."""
    if crop not in CROP_DATABASE:
        return []
    
    crop_info = CROP_DATABASE[crop]
    schemes = crop_info.get("government_schemes", [])
    
    # Add scheme details
    scheme_details = {
        "PM-KISAN": {"name": "PM-KISAN", "benefit": "₹6000/year direct transfer", "eligibility": "All farmers"},
        "PMFBY": {"name": "Pradhan Mantri Fasal Bima Yojana", "benefit": "Crop insurance at 1.5-2% premium", "eligibility": "All farmers"},
        "Paddy Procurement at MSP": {"name": "Paddy MSP Procurement", "benefit": f"Guaranteed MSP of ₹{CROP_DATABASE.get(crop, {}).get('msp_2024', 'N/A')}/quintal", "eligibility": "Registered farmers"},
        "Wheat Procurement": {"name": "Wheat MSP Procurement", "benefit": f"Guaranteed MSP of ₹{CROP_DATABASE.get(crop, {}).get('msp_2024', 'N/A')}/quintal", "eligibility": "Registered farmers"},
        "e-NAM": {"name": "e-NAM (National Agriculture Market)", "benefit": "Online trading, better prices", "eligibility": "All farmers"},
        "NAFED Procurement": {"name": "NAFED Procurement", "benefit": f"Procurement at MSP ₹{CROP_DATABASE.get(crop, {}).get('msp_2024', 'N/A')}/quintal", "eligibility": "Registered farmers"},
        "Pulses Procurement": {"name": "Pulses Procurement Scheme", "benefit": "Assured procurement at MSP", "eligibility": "Registered farmers"},
        "Cotton Corporation of India Procurement": {"name": "CCI Cotton Procurement", "benefit": f"MSP of ₹{CROP_DATABASE.get(crop, {}).get('msp_2024', 'N/A')}/quintal", "eligibility": "Cotton farmers"},
        "Sugar Development Fund": {"name": "Sugar Development Fund", "benefit": "Loans for cane development", "eligibility": "Sugarcane farmers"},
        "Cold Storage Subsidy": {"name": "Cold Storage Subsidy Scheme", "benefit": "35-50% subsidy on cold storage", "eligibility": "FPOs, farmers"}
    }
    
    return [scheme_details.get(s, {"name": s, "benefit": "Various benefits", "eligibility": "Check with local office"}) for s in schemes]


def _calculate_confidence(crop: str, soil_data: Dict, weather_data: Dict) -> float:
    """Calculate confidence score 0-1 for crop recommendation."""
    confidence = 0.7  # Base confidence

    # Soil factor
    soil_health = soil_data.get("health_score", 5) / 10.0
    soil_confidence = soil_data.get("health_confidence", 0.5)
    confidence *= (0.4 + 0.6 * soil_health) * (0.5 + 0.5 * soil_confidence)

    # Weather factor
    weather_score = weather_data.get("suitability_score", 5) / 10.0
    weather_confidence = weather_data.get("suitability_confidence", 0.5)
    confidence *= (0.4 + 0.6 * weather_score) * (0.5 + 0.5 * weather_confidence)

    # Crop-soil compatibility from database
    if crop in CROP_DATABASE:
        crop_info = CROP_DATABASE[crop]
        soil_type = soil_data.get("soil_type", "unknown")
        if soil_type in crop_info.get("suitable_soil", []):
            confidence *= 1.15  # Boost for matching soil
        else:
            confidence *= 0.85  # Penalty for non-ideal soil
        
        # MSP availability adds confidence
        if crop_info.get("msp_2024"):
            confidence *= 1.05

    return round(min(1.0, confidence), 2)


def _generate_reasoning(crop: str, soil_data: Dict, weather_data: Dict, crop_info: Dict = None) -> str:
    """Generate detailed reasoning for crop recommendation."""
    soil_type = soil_data.get("soil_type", "unknown")
    season = weather_data.get("season", "kharif")
    
    reasons = []
    
    # Soil suitability
    if crop_info:
        if soil_type in crop_info.get("suitable_soil", []):
            reasons.append(f"well-suited for {soil_type} soil")
        
        # Water requirement
        water_req = crop_info.get("water_requirement", "moderate")
        rainfall = weather_data.get("rainfall_mm", 500)
        if water_req == "low" and rainfall < 400:
            reasons.append("low water requirement matches rainfall")
        elif water_req == "high" and rainfall > 800:
            reasons.append("adequate rainfall for high water needs")
        
        # MSP availability
        if crop_info.get("msp_2024"):
            reasons.append(f"MSP of ₹{crop_info['msp_2024']}/quintal ensures price security")
    
    # Season suitability
    reasons.append(f"suitable for {season} season")
    
    reasoning = f"{crop.capitalize()} is recommended because it is " + ", ".join(reasons) if reasons else f"{crop.capitalize()} is a suitable crop for current conditions"
    
    return reasoning


def _estimate_yield(crop: str, soil_health: int, crop_info: Dict = None) -> Dict[str, Any]:
    """Estimate expected yield based on soil health and crop data."""
    if crop_info:
        base_yield = crop_info.get("expected_yield_kg_ha", 2000)
    else:
        base_yields = {
            "rice": 4500, "wheat": 4000, "maize": 5000,
            "cotton": 2000, "soybean": 2200, "groundnut": 2000,
            "chickpea": 1800, "mustard": 1500, "sugarcane": 70000,
            "potato": 25000
        }
        base_yield = base_yields.get(crop, 2000)

    # Adjust based on soil health
    if soil_health >= 8:
        multiplier = 1.15
        quality = "optimal"
    elif soil_health >= 6:
        multiplier = 1.0
        quality = "good"
    elif soil_health >= 4:
        multiplier = 0.85
        quality = "moderate"
    else:
        multiplier = 0.7
        quality = "challenging"

    adjusted_yield = int(base_yield * multiplier)
    
    return {
        "kg_per_ha": adjusted_yield,
        "range": f"{int(adjusted_yield * 0.85)}-{int(adjusted_yield * 1.1)} kg/ha",
        "quality_factor": quality,
        "soil_health_impact": f"{int((multiplier - 1) * 100):+d}% from soil conditions"
    }


def _get_crop_duration(crop: str, season: str) -> int:
    """Get crop duration in months."""
    durations = {
        "rice": 4, "wheat": 5, "maize": 4, "cotton": 6,
        "soybean": 4, "groundnut": 4, "chickpea": 4, "mustard": 4,
        "sugarcane": 12, "potato": 4, "barley": 5, "millet": 3,
        "sorghum": 4
    }
    return durations.get(crop, 4)


def _find_alternatives(recommendations: List[Dict], soil_data: Dict, weather_data: Dict) -> List[Dict]:
    """Find alternative crops with reasoning if primary recommendations are not feasible."""
    alternatives = []

    # Get primary crop names
    primary_crops = [r["name"] for r in recommendations]
    season = weather_data.get("season", "kharif")
    soil_type = soil_data.get("soil_type", "unknown")

    # Alternative crops by season with lower input requirements
    low_input_alternatives = {
        "kharif": [
            {"crop": "millet", "reason": "Low water requirement, drought resistant"},
            {"crop": "sorghum", "reason": "Hardy crop, good fodder value"},
            {"crop": "pigeonpea", "reason": "Nitrogen fixing, low input needs"}
        ],
        "rabi": [
            {"crop": "lentil", "reason": "Short duration, nitrogen fixing"},
            {"crop": "pea", "reason": "Low water requirement, good market"},
            {"crop": "linseed", "reason": "Drought tolerant, dual purpose (seed + oil)"}
        ],
        "zaid": [
            {"crop": "cucumber", "reason": "Short duration, good market price"},
            {"crop": "watermelon", "reason": "Heat tolerant, high value"},
            {"crop": "moong", "reason": "Short duration, nitrogen fixing"}
        ]
    }

    season_alternatives = low_input_alternatives.get(season, low_input_alternatives["kharif"])
    
    for alt in season_alternatives:
        if alt["crop"] not in primary_crops:
            alternatives.append({
                "crop": alt["crop"],
                "reason": alt["reason"],
                "type": "low_input_alternative"
            })

    # Add soil-specific alternatives
    if soil_type == "sandy" and "groundnut" not in primary_crops:
        alternatives.append({"crop": "groundnut", "reason": "Ideal for sandy soil drainage", "type": "soil_specific"})
    elif soil_type == "clay" and "rice" not in primary_crops:
        alternatives.append({"crop": "rice", "reason": "Clay soil water retention suits rice", "type": "soil_specific"})

    return alternatives[:5]


def _assess_risks(soil_data: Dict, weather_data: Dict, recommendations: List[Dict]) -> List[Dict]:
    """Assess comprehensive risks for recommended crops."""
    risks = []

    # Soil-based risks
    soil_constraints = soil_data.get("constraints", [])
    for constraint in soil_constraints:
        if "waterlogging" in constraint.lower():
            risks.append({
                "type": "soil",
                "severity": "moderate",
                "description": "Waterlogging risk in monsoon - avoid flood-sensitive crops",
                "affected_crops": ["groundnut", "chickpea", "mustard"]
            })
        elif "low water retention" in constraint.lower():
            risks.append({
                "type": "soil",
                "severity": "moderate", 
                "description": "Sandy soil needs frequent irrigation",
                "affected_crops": ["rice", "sugarcane"]
            })

    # Weather-based risks
    risk_assessment = weather_data.get("risk_assessment", {})
    
    if risk_assessment.get("drought", {}).get("level") in ["moderate", "high"]:
        risks.append({
            "type": "weather",
            "severity": risk_assessment["drought"]["level"],
            "description": "Drought risk - plan irrigation or choose drought-tolerant varieties",
            "affected_crops": ["rice", "sugarcane", "maize"]
        })
    
    if risk_assessment.get("flood", {}).get("level") in ["moderate", "high"]:
        risks.append({
            "type": "weather",
            "severity": risk_assessment["flood"]["level"],
            "description": "Heavy rainfall may cause flooding - ensure drainage",
            "affected_crops": ["groundnut", "potato", "onion"]
        })
    
    if risk_assessment.get("disease_pressure", {}).get("level") in ["moderate", "high"]:
        risks.append({
            "type": "disease",
            "severity": risk_assessment["disease_pressure"]["level"],
            "description": "High humidity increases fungal disease risk",
            "affected_crops": ["rice", "potato", "tomato"]
        })

    # Market risks
    risks.append({
        "type": "market",
        "severity": "low",
        "description": "Price volatility possible - consider MSP-covered crops",
        "mitigation": "Register with local procurement agency"
    })

    return risks


def _suggest_precautions(risks: List[Dict], weather_data: Dict) -> List[Dict]:
    """Suggest precautions based on identified risks."""
    precautions = []

    risk_types = [r.get("type") for r in risks]
    
    if "weather" in risk_types:
        drought_level = weather_data.get("risk_assessment", {}).get("drought", {}).get("level", "none")
        if drought_level in ["moderate", "high"]:
            precautions.extend([
                {"action": "Install drip/sprinkler irrigation", "priority": "high", "timing": "before_sowing"},
                {"action": "Use drought-resistant varieties", "priority": "high", "timing": "seed_selection"},
                {"action": "Apply mulch to conserve moisture", "priority": "medium", "timing": "after_germination"}
            ])
        
        flood_level = weather_data.get("risk_assessment", {}).get("flood", {}).get("level", "none")
        if flood_level in ["moderate", "high"]:
            precautions.extend([
                {"action": "Create drainage channels", "priority": "high", "timing": "before_sowing"},
                {"action": "Use raised bed cultivation", "priority": "medium", "timing": "land_preparation"},
                {"action": "Keep flood-tolerant varieties ready", "priority": "medium", "timing": "seed_selection"}
            ])

    if "disease" in risk_types:
        precautions.extend([
            {"action": "Apply preventive fungicide spray", "priority": "medium", "timing": "regular_intervals"},
            {"action": "Maintain proper plant spacing", "priority": "medium", "timing": "sowing"},
            {"action": "Remove infected plants immediately", "priority": "high", "timing": "monitoring"}
        ])

    if "soil" in risk_types:
        precautions.extend([
            {"action": "Apply soil amendments as recommended", "priority": "high", "timing": "before_sowing"},
            {"action": "Practice crop rotation", "priority": "medium", "timing": "planning"},
            {"action": "Add organic matter to improve soil structure", "priority": "medium", "timing": "land_preparation"}
        ])

    # General precautions
    precautions.extend([
        {"action": "Get crop insurance under PMFBY", "priority": "high", "timing": "before_sowing"},
        {"action": "Register for MSP procurement if applicable", "priority": "medium", "timing": "pre_harvest"},
        {"action": "Maintain records for scheme benefits", "priority": "low", "timing": "ongoing"}
    ])

    return precautions[:10]