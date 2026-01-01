from lambda.embeddings.embed import embed_text
from lambda.embeddings.pinecone_client import query_embedding

def retrieve_documents(query):
    query_vector = embed_text(query)
    results = query_embedding(query_vector, top_k=5)
    docs = []
    for match in results:
        docs.append({
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata
        })
    return docs
