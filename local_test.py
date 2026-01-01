#!/usr/bin/env python3
"""
Local test script to run the Farmer RAG Lambda without Docker.
This simulates the Lambda handler locally.

Usage:
    python local_test.py "What crops are best for sandy soil?"
    
Before running:
1. Set your PINECONE_API_KEY environment variable:
   export PINECONE_API_KEY="your-api-key"
   
2. Ensure you have AWS credentials configured:
   aws configure
"""

import sys
import os

# IMPORTANT: Set environment variables BEFORE any imports
# Update these with your actual values or set them in your shell
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("EMBED_MODEL", "amazon.titan-embed-text-v2:0")
os.environ.setdefault("LLM_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
os.environ.setdefault("PINECONE_INDEX", "farmer-rag-index")
# PINECONE_API_KEY should be set via environment variable for security

# Add the project root to path so 'lambda' package can be found
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def main():
    if len(sys.argv) < 2:
        print("Usage: python local_test.py \"Your question here\"")
        print("Example: python local_test.py \"What crops are best for sandy soil?\"")
        print("\nMake sure to set PINECONE_API_KEY environment variable first:")
        print("  export PINECONE_API_KEY=\"your-api-key\"")
        sys.exit(1)
    
    # Check for required environment variables
    if not os.environ.get("PINECONE_API_KEY"):
        print("❌ Error: PINECONE_API_KEY environment variable is not set")
        print("Set it with: export PINECONE_API_KEY=\"your-api-key\"")
        sys.exit(1)
    
    query = sys.argv[1]
    
    # Create a mock Lambda event
    event = {
        "queryStringParameters": {
            "query": query
        }
    }
    
    print(f"\n🔍 Query: {query}\n")
    print("=" * 50)
    
    try:
        # Import the handler (this will use the src.* imports)
        from src.handler import lambda_handler
        
        print("📚 Retrieving documents, building prompt, and calling LLM...")
        
        # Call the Lambda handler
        response = lambda_handler(event, {})
        
        print("\n" + "=" * 50)
        print(f"✅ Status: {response['statusCode']}")
        print(f"📝 Response:\n{response['body']}")
        
        return response
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": str(e)
        }


if __name__ == "__main__":
    main()
