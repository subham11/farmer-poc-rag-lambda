import json
from rag.retrieve import retrieve_documents
from rag.prompt import build_prompt
from llm.bedrock_client import call_llm
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
        elif event.get("queryStringParameters"):
            query = event["queryStringParameters"].get("query") or event["queryStringParameters"].get("question")
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

        docs = retrieve_documents(query)
        prompt = build_prompt(query, docs)
        answer = call_llm(prompt)

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"question": query, "answer": answer})
        }

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)})
        }
