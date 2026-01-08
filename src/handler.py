import json
from rag.retrieve import retrieve_documents
from rag.prompt import build_prompt
from llm.bedrock_client import call_llm
from agents.orchestrator import orchestrate_query
from agents.weather_agent import enrich_context_from_pincode
from utils.logger import logger

# CORS headers for API Gateway responses
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Session-Id,X-Language",
}

def lambda_handler(event, context):
    logger.info(event)

    try:
        # Support both POST (JSON body) and GET (query string)
        if event.get("body"):
            body = json.loads(event["body"])
            query = body.get("question") or body.get("query")
            use_agents = body.get("use_agents", True)  # Default to multi-agent
            # Extract location context
            user_context = {
                "pincode": body.get("pincode"),
                "district": body.get("district"),
                "state": body.get("state"),
                "language": body.get("language", "en"),
                "user_profile": body.get("user_profile", {})
            }
        elif event.get("queryStringParameters"):
            params = event["queryStringParameters"]
            query = params.get("query") or params.get("question")
            use_agents = params.get("use_agents", "true").lower() == "true"
            # Extract location context from query params
            user_context = {
                "pincode": params.get("pincode"),
                "district": params.get("district"),
                "state": params.get("state"),
                "language": params.get("language", "en"),
                "user_profile": {}
            }
        else:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "No question provided. Use POST with JSON body or GET with query parameter."})
            }

        if not query:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Question/query parameter is required."})
            }

        # Enrich context from pincode if provided (uses India Post API)
        if user_context.get("pincode"):
            user_context = enrich_context_from_pincode(user_context)
            logger.info(f"Enriched context: state={user_context.get('state')}, district={user_context.get('district')}")

        if use_agents:
            # Use multi-agent system with context
            agent_result = orchestrate_query(query, user_context)
            prompt = agent_result.get("llm_prompt_input", f"Query: {query}")
            answer = call_llm(prompt)
            response_body = {
                "question": query,
                "answer": answer,
                "agents_used": agent_result.get("agents_invoked", []),
                "analysis": {
                    "soil": agent_result.get("soil_data"),
                    "weather": agent_result.get("weather_data"),
                    "crop_plan": agent_result.get("crop_plan")
                }
            }
        else:
            # Use traditional RAG pipeline
            docs = retrieve_documents(query)
            prompt = build_prompt(query, docs)
            answer = call_llm(prompt)
            response_body = {"question": query, "answer": answer}

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(response_body)
        }

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)})
        }
