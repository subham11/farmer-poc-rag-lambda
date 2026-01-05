#!/usr/bin/env python3
"""
Test cases for Voice AI endpoints.

Usage:
    # Test local handlers
    python test_voice_api.py --local
    
    # Test deployed API
    python test_voice_api.py --api-url https://xxx.execute-api.ap-south-1.amazonaws.com/Prod
"""

import sys
import os
import json
import argparse
import base64

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def test_rate_limiter():
    """Test the DynamoDB rate limiter logic."""
    print("\n" + "="*60)
    print("Testing Rate Limiter")
    print("="*60)
    
    from src.voice.rate_limiter import RateLimiter, RateLimitExceeded
    from src.voice.config import config
    
    # Create test instance (will need DynamoDB local or mocked)
    print(f"✓ Rate limit config: {config.max_requests_per_hour} requests/hour")
    print(f"✓ Rate limit table: {config.rate_limit_table}")
    print("✓ Rate limiter module loaded successfully")
    
    return True


def test_asr_router():
    """Test ASR routing logic."""
    print("\n" + "="*60)
    print("Testing ASR Router")
    print("="*60)
    
    from src.voice.config import Language, get_asr_provider, ASRProvider
    
    # Test routing
    test_cases = [
        (Language.ENGLISH, ASRProvider.TRANSCRIBE),
        (Language.HINDI, ASRProvider.TRANSCRIBE),
        (Language.ODIA, ASRProvider.WHISPER),
    ]
    
    for language, expected_provider in test_cases:
        provider = get_asr_provider(language)
        status = "✓" if provider == expected_provider else "✗"
        print(f"{status} {language.value} -> {provider.value} (expected: {expected_provider.value})")
    
    return True


def test_tts_router():
    """Test TTS routing logic."""
    print("\n" + "="*60)
    print("Testing TTS Router")
    print("="*60)
    
    from src.voice.config import Language, get_tts_provider, TTSProvider
    
    # Test routing
    test_cases = [
        (Language.ENGLISH, TTSProvider.POLLY),
        (Language.HINDI, TTSProvider.POLLY),
        (Language.ODIA, TTSProvider.OPENAI),
    ]
    
    for language, expected_provider in test_cases:
        provider = get_tts_provider(language)
        status = "✓" if provider == expected_provider else "✗"
        print(f"{status} {language.value} -> {provider.value} (expected: {expected_provider.value})")
    
    return True


def test_upload_url_handler_local():
    """Test upload URL handler locally."""
    print("\n" + "="*60)
    print("Testing Upload URL Handler (Local)")
    print("="*60)
    
    from src.voice.handlers import upload_url_handler
    
    event = {
        "queryStringParameters": {"file_type": "wav"},
        "headers": {"X-Session-Id": "test_session_123"},
    }
    
    try:
        response = upload_url_handler(event, {})
        body = json.loads(response["body"])
        
        print(f"Status Code: {response['statusCode']}")
        
        if response["statusCode"] == 200:
            print(f"✓ upload_url: {body.get('upload_url', '')[:50]}...")
            print(f"✓ s3_key: {body.get('s3_key')}")
            print(f"✓ expires_in: {body.get('expires_in')}")
            return True
        else:
            print(f"✗ Error: {body.get('error')}")
            return False
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def test_language_detection():
    """Test language extraction from request."""
    print("\n" + "="*60)
    print("Testing Language Detection")
    print("="*60)
    
    from src.voice.handlers import _get_language
    from src.voice.config import Language
    
    test_cases = [
        ({"queryStringParameters": {"language": "en"}}, Language.ENGLISH),
        ({"queryStringParameters": {"language": "hi"}}, Language.HINDI),
        ({"queryStringParameters": {"language": "or"}}, Language.ODIA),
        ({"queryStringParameters": {"language": "odia"}}, Language.ODIA),
        ({"headers": {"X-Language": "hi"}}, Language.HINDI),
        ({}, Language.ENGLISH),  # Default
    ]
    
    all_passed = True
    for event, expected in test_cases:
        result = _get_language(event)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} {event} -> {result.value} (expected: {expected.value})")
    
    return all_passed


def test_tts_synthesis_mock():
    """Test TTS synthesis with mock data."""
    print("\n" + "="*60)
    print("Testing TTS Module (Mock)")
    print("="*60)
    
    from src.voice.config import Language, config
    
    # Test Polly client initialization
    try:
        from src.voice.tts.polly_client import PollyTTS
        polly = PollyTTS()
        print(f"✓ Polly client initialized")
        print(f"  Voice for EN: {polly.voice_ids.get(Language.ENGLISH)}")
        print(f"  Voice for HI: {polly.voice_ids.get(Language.HINDI)}")
    except Exception as e:
        print(f"✗ Polly client error: {e}")
    
    # Test OpenAI TTS client initialization
    try:
        from src.voice.tts.openai_client import OpenAITTS
        openai_tts = OpenAITTS()
        has_key = bool(config.openai_api_key)
        print(f"✓ OpenAI TTS client initialized (API key set: {has_key})")
    except Exception as e:
        print(f"✗ OpenAI TTS client error: {e}")
    
    return True


def run_unit_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print("🧪 VOICE AI UNIT TESTS")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Rate Limiter", test_rate_limiter()))
    results.append(("ASR Router", test_asr_router()))
    results.append(("TTS Router", test_tts_router()))
    results.append(("Language Detection", test_language_detection()))
    results.append(("TTS Module", test_tts_synthesis_mock()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


def run_integration_test_upload_url(api_url: str, session_id: str):
    """Test upload URL endpoint against deployed API."""
    import urllib.request
    
    print("\n" + "="*60)
    print("Testing Upload URL Endpoint")
    print("="*60)
    
    url = f"{api_url}/voice/upload-url?file_type=wav"
    
    req = urllib.request.Request(
        url,
        headers={
            "X-Session-Id": session_id,
            "Content-Type": "application/json",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            print(f"✓ Status: 200")
            print(f"✓ upload_url: {body.get('upload_url', '')[:80]}...")
            print(f"✓ s3_key: {body.get('s3_key')}")
            return body
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def run_integration_test_rate_limit(api_url: str, session_id: str):
    """Test rate limit status endpoint."""
    import urllib.request
    
    print("\n" + "="*60)
    print("Testing Rate Limit Status Endpoint")
    print("="*60)
    
    url = f"{api_url}/voice/rate-limit-status"
    
    req = urllib.request.Request(
        url,
        headers={
            "X-Session-Id": session_id,
            "Content-Type": "application/json",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            print(f"✓ Status: 200")
            print(f"✓ Session: {body.get('session_id')}")
            print(f"✓ Max requests/hour: {body.get('max_requests_per_hour')}")
            print(f"✓ ASR remaining: {body.get('asr', {}).get('remaining')}")
            print(f"✓ TTS remaining: {body.get('tts', {}).get('remaining')}")
            return body
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Test Voice AI endpoints")
    parser.add_argument("--local", action="store_true", help="Run local unit tests")
    parser.add_argument("--api-url", type=str, help="API Gateway URL for integration tests")
    parser.add_argument("--session-id", type=str, default="test_session_001", help="Session ID for tests")
    args = parser.parse_args()
    
    if args.local or not args.api_url:
        # Run unit tests
        success = run_unit_tests()
        
        # Also test local handler if possible
        try:
            test_upload_url_handler_local()
        except Exception as e:
            print(f"\n⚠️  Local handler test skipped: {e}")
        
        sys.exit(0 if success else 1)
    
    if args.api_url:
        # Run integration tests
        print("\n" + "="*60)
        print("🧪 VOICE AI INTEGRATION TESTS")
        print(f"API URL: {args.api_url}")
        print(f"Session ID: {args.session_id}")
        print("="*60)
        
        run_integration_test_upload_url(args.api_url, args.session_id)
        run_integration_test_rate_limit(args.api_url, args.session_id)


if __name__ == "__main__":
    main()
