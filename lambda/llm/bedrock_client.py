import boto3
from lambda.config import AWS_REGION, LLM_MODEL

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def call_llm(prompt):
    safe_prompt = prompt.replace('"', "'")
    response = bedrock.invoke_model(
        modelId=LLM_MODEL,
        contentType="application/json",
        accept="application/json",
        body='{"messages":[{"role":"user","content":"' + safe_prompt + '"}]}'
    )
    output = response["body"].read().decode()
    return eval(output)["output_text"]
