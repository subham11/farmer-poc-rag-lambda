import pinecone
from lambda.config import PINECONE_API_KEY, PINECONE_INDEX

pinecone.init(api_key=PINECONE_API_KEY)
index = pinecone.Index(PINECONE_INDEX)

def store_embedding(id, vector, metadata):
    index.upsert([(id, vector, metadata)])

def query_embedding(vector, top_k=5):
    return index.query(vector=vector, top_k=top_k, include_metadata=True).matches
