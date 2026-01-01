from lambda.rag.retrieve import retrieve_documents
from lambda.rag.prompt import build_prompt
from lambda.llm.bedrock_client import call_llm
from lambda.utils.logger import logger

def lambda_handler(event, context):
    logger.info(event)

    query = event["queryStringParameters"]["query"]

    docs = retrieve_documents(query)
    prompt = build_prompt(query, docs)
    answer = call_llm(prompt)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": answer
    }
