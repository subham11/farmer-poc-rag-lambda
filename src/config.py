import os

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX = os.environ.get("PINECONE_INDEX", "farmer-rag-index")

S3_BUCKET = os.environ.get("S3_BUCKET")

EMBED_MODEL = os.environ.get("EMBED_MODEL", "amazon.titan-embed-text-v2")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
