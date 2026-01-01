import boto3
import json
from config import AWS_REGION, LLM_MODEL

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def call_llm(prompt):
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
    
    response = bedrock.invoke_model(
        modelId=LLM_MODEL,
        contentType="application/json",
        accept="application/json",
        body=body
    )
    
    result = json.loads(response["body"].read().decode())
    return result["content"][0]["text"]
