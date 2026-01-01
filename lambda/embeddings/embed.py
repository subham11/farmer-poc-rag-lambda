import boto3
from lambda.config import AWS_REGION, EMBED_MODEL

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def embed_text(text):
    response = bedrock.invoke_model(
        modelId=EMBED_MODEL,
        contentType="application/json",
        accept="application/json",
        body='{"inputText": "' + text.replace('"', "'") + '"}'
    )
    result = response["body"].read().decode()
    return eval(result)["embedding"]
