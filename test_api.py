#!/usr/bin/env python3
"""
Test cases for Farmer RAG API.

Usage:
    # Test deployed API
    python test_api.py
    
    # Test local Lambda handler
    python test_api.py --local
    
    # Test specific case
    python test_api.py --case 1
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse

# API endpoint
API_URL = "https://1xige88h50.execute-api.ap-south-1.amazonaws.com/Prod/ask"

# Test cases
TEST_CASES = [
    {
        "id": 1,
        "name": "Clay soil crops",
        "query": "What crops grow well in clay soil",
        "expected_keywords": ["wheat", "millet", "soybean", "pigeon pea"],
    },
    {
        "id": 2,
        "name": "Punjab crops (no data)",
        "query": "What are the recommended crops in Punjab",
        "expected_keywords": ["punjab", "not", "information"],  # Should indicate no data
    },
    {
        "id": 3,
        "name": "Rainy weather crops",
        "query": "Which crops are suitable for rainy weather",
        "expected_keywords": ["paddy", "sugarcane", "rainy", "monsoon"],
    },
    {
        "id": 4,
        "name": "Wheat growing states",
        "query": "In which states is wheat grown",
        "expected_keywords": ["uttar pradesh", "andhra pradesh", "chhattisgarh", "odisha"],
    },
    {
        "id": 5,
        "name": "Black soil + dry weather",
        "query": "What crops are best for black soil in dry weather",
        "expected_keywords": ["groundnut", "soybean", "black soil"],
    },
]


def test_deployed_api(query: str) -> str:
    """Test the deployed API endpoint."""
    encoded_query = urllib.parse.quote(query)
    url = f"{API_URL}?query={encoded_query}"
    
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def test_local_handler(query: str) -> str:
    """Test the local Lambda handler."""
    # Set environment variables
    os.environ.setdefault("AWS_REGION", "ap-south-1")
    os.environ.setdefault("EMBED_MODEL", "amazon.titan-embed-text-v2:0")
    os.environ.setdefault("LLM_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
    os.environ.setdefault("PINECONE_INDEX", "farmer-rag-index")
    
    if not os.environ.get("PINECONE_API_KEY"):
        raise ValueError("PINECONE_API_KEY environment variable is not set")
    
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    from src.handler import lambda_handler
    
    event = {"queryStringParameters": {"query": query}}
    response = lambda_handler(event, {})
    
    return response["body"]


def check_keywords(response: str, keywords: list) -> tuple:
    """Check if response contains expected keywords."""
    response_lower = response.lower()
    found = []
    missing = []
    
    for keyword in keywords:
        if keyword.lower() in response_lower:
            found.append(keyword)
        else:
            missing.append(keyword)
    
    return found, missing


def run_test(test_case: dict, use_local: bool = False) -> bool:
    """Run a single test case."""
    print(f"\n{'='*60}")
    print(f"Test {test_case['id']}: {test_case['name']}")
    print(f"{'='*60}")
    print(f"Query: {test_case['query']}")
    print("-" * 60)
    
    try:
        if use_local:
            response = test_local_handler(test_case["query"])
        else:
            response = test_deployed_api(test_case["query"])
        
        print(f"Response:\n{response}")
        print("-" * 60)
        
        # Check for expected keywords
        found, missing = check_keywords(response, test_case["expected_keywords"])
        
        if found:
            print(f"✅ Found keywords: {', '.join(found)}")
        
        if missing:
            print(f"⚠️  Missing keywords: {', '.join(missing)}")
        
        # Consider test passed if at least half the keywords are found
        passed = len(found) >= len(test_case["expected_keywords"]) / 2
        
        if passed:
            print("✅ TEST PASSED")
        else:
            print("❌ TEST FAILED")
        
        return passed
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Farmer RAG API")
    parser.add_argument("--local", action="store_true", help="Test local handler instead of deployed API")
    parser.add_argument("--case", type=int, help="Run specific test case (1-5)")
    args = parser.parse_args()
    
    mode = "LOCAL" if args.local else "DEPLOYED API"
    print(f"\n🧪 Running Farmer RAG Tests ({mode})")
    print(f"{'='*60}")
    
    if args.case:
        # Run specific test case
        test_cases = [tc for tc in TEST_CASES if tc["id"] == args.case]
        if not test_cases:
            print(f"❌ Test case {args.case} not found. Available: 1-5")
            sys.exit(1)
    else:
        test_cases = TEST_CASES
    
    results = []
    for test_case in test_cases:
        passed = run_test(test_case, use_local=args.local)
        results.append((test_case["id"], test_case["name"], passed))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed_count = sum(1 for _, _, p in results if p)
    total_count = len(results)
    
    for test_id, name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  Test {test_id}: {name} - {status}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
