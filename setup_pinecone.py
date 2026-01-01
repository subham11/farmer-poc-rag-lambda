#!/usr/bin/env python3
"""
Setup script to create Pinecone index and ingest farmer data.
Run this once before using the RAG system.

Usage:
    export PINECONE_API_KEY="your-api-key"
    python setup_pinecone.py
"""

import os
import sys
import time

# Set environment variables before imports
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("EMBED_MODEL", "amazon.titan-embed-text-v2:0")
os.environ.setdefault("PINECONE_INDEX", "farmer-rag-index")

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from pinecone import Pinecone, ServerlessSpec

def main():
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        print("❌ Error: PINECONE_API_KEY environment variable is not set")
        sys.exit(1)
    
    index_name = os.environ.get("PINECONE_INDEX", "farmer-rag-index")
    
    print("🔧 Connecting to Pinecone...")
    pc = Pinecone(api_key=api_key)
    
    # Check if index exists
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    
    if index_name in existing_indexes:
        print(f"✅ Index '{index_name}' already exists")
    else:
        print(f"📦 Creating index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=1024,  # Titan Embeddings v2 dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"  # Pinecone serverless region
            )
        )
        print("⏳ Waiting for index to be ready...")
        time.sleep(10)
    
    # Load and ingest data
    print("\n📊 Loading farmer dataset...")
    import pandas as pd
    from src.embeddings.embed import embed_text
    
    df = pd.read_csv(os.path.join(project_root, "data", "farmer_dataset.csv"))
    print(f"   Found {len(df)} records")
    
    index = pc.Index(index_name)
    
    print("\n🚀 Ingesting data (this may take a few minutes)...")
    vectors_to_upsert = []
    
    for i, row in df.iterrows():
        # Create text representation for embedding
        text = f"Farmer {row.get('farmer_name', 'Unknown')} in {row.get('location_state', 'Unknown')} with {row.get('soil_type', 'Unknown')} soil. Recommended crop: {row.get('recommended_crop', 'Unknown')}. Weather: {row.get('weather_condition', 'Unknown')}."
        
        print(f"   Processing record {i+1}/{len(df)}...", end="\r")
        
        try:
            embedding = embed_text(text)
            
            metadata = {
                "farmer_name": str(row.get('farmer_name', '')),
                "location_state": str(row.get('location_state', '')),
                "soil_type": str(row.get('soil_type', '')),
                "recommended_crop": str(row.get('recommended_crop', '')),
                "weather_condition": str(row.get('weather_condition', '')),
                "text": text
            }
            
            vectors_to_upsert.append({
                "id": f"farmer_{i}",
                "values": embedding,
                "metadata": metadata
            })
            
            # Batch upsert every 50 records
            if len(vectors_to_upsert) >= 50:
                index.upsert(vectors=vectors_to_upsert)
                vectors_to_upsert = []
                
        except Exception as e:
            print(f"\n   ⚠️  Error processing record {i}: {e}")
            continue
    
    # Upsert remaining vectors
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert)
    
    print(f"\n\n✅ Successfully ingested {len(df)} records into Pinecone!")
    print(f"\n🎉 Setup complete! You can now run:")
    print(f'   python local_test.py "What crops are best for sandy soil?"')


if __name__ == "__main__":
    main()
