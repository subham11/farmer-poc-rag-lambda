from pinecone import Pinecone
from config import PINECONE_API_KEY, PINECONE_INDEX

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

def store_embedding(id, vector, metadata):
    index.upsert(vectors=[(id, vector, metadata)])

def query_embedding(vector, top_k=5):
    return index.query(vector=vector, top_k=top_k, include_metadata=True).matches
