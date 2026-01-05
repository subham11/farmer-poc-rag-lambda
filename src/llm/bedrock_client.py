import boto3
import json
from config import AWS_REGION, LLM_MODEL
from utils.logger import logger

# Lazy initialization
_bedrock = None

def _get_bedrock_client():
    """Lazily initialize Bedrock client."""
    global _bedrock
    if _bedrock is None:
        logger.info(f"Initializing Bedrock client in region: {AWS_REGION}")
        _bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    return _bedrock

def call_llm(prompt):
    logger.info(f"Calling LLM model: {LLM_MODEL}")
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })
    
    try:
        bedrock = _get_bedrock_client()
        response = bedrock.invoke_model(
            modelId=LLM_MODEL,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        
        result = json.loads(response["body"].read().decode())
        return result["content"][0]["text"]
    except Exception as e:
        logger.error(f"Bedrock LLM error: {e}")
        raise
