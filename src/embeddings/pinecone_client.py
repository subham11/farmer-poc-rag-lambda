from pinecone import Pinecone
from config import PINECONE_API_KEY, PINECONE_INDEX
from utils.logger import logger

# Lazy initialization to prevent crashes at import time
_pc = None
_index = None

def _get_index():
    """Lazily initialize Pinecone connection."""
    global _pc, _index
    if _index is None:
        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY environment variable is not set")
        logger.info(f"Initializing Pinecone with index: {PINECONE_INDEX}")
        _pc = Pinecone(api_key=PINECONE_API_KEY)
        _index = _pc.Index(PINECONE_INDEX)
    return _index

def store_embedding(id, vector, metadata):
    index = _get_index()
    index.upsert(vectors=[(id, vector, metadata)])

def query_embedding(vector, top_k=5):
    index = _get_index()
    return index.query(vector=vector, top_k=top_k, include_metadata=True).matches
