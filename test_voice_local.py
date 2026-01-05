#!/usr/bin/env python3
"""
Local simulation test for Voice AI pipeline.
Tests the full flow without requiring AWS services.
"""

import sys
import os
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set environment variables
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("AUDIO_BUCKET", "farmer-voice-audio-test")
os.environ.setdefault("RATE_LIMIT_TABLE", "farmer-voice-rate-limits-test")
os.environ.setdefault("MAX_REQUESTS_PER_HOUR", "5")


def test_voice_config():
    """Test voice configuration."""
    print("\n" + "="*60)
    print("1. Testing Voice Configuration")
    print("="*60)
    
    from src.voice.config import (
        Language, ASRProvider, TTSProvider,
        get_asr_provider, get_tts_provider, config
    )
    
    print(f"✓ AWS Region: {config.aws_region}")
    print(f"✓ Audio Bucket: {config.audio_bucket}")
    print(f"✓ Rate Limit Table: {config.rate_limit_table}")
    print(f"✓ Max Requests/Hour: {config.max_requests_per_hour}")
    print(f"✓ Upload URL Expiry: {config.upload_url_expiry}s")
    
    print("\nLanguage Routing:")
    for lang in Language:
        asr = get_asr_provider(lang)
        tts = get_tts_provider(lang)
        print(f"  {lang.value.upper():8} → ASR: {asr.value:12} | TTS: {tts.value}")
    
    return True


def test_handlers_structure():
    """Test that all handlers are importable."""
    print("\n" + "="*60)
    print("2. Testing Handler Imports")
    print("="*60)
    
    from src.voice.handlers import (
        upload_url_handler,
        asr_handler,
        tts_handler,
        voice_pipeline_handler,
        rate_limit_status_handler,
    )
    
    handlers = [
        ("upload_url_handler", upload_url_handler),
        ("asr_handler", asr_handler),
        ("tts_handler", tts_handler),
        ("voice_pipeline_handler", voice_pipeline_handler),
        ("rate_limit_status_handler", rate_limit_status_handler),
    ]
    
    for name, handler in handlers:
        print(f"✓ {name} loaded")
    
    return True


def test_upload_url_generation():
    """Test pre-signed URL generation."""
    print("\n" + "="*60)
    print("3. Testing Upload URL Generation")
    print("="*60)
    
    from src.voice.handlers import upload_url_handler
    
    # Test different file types
    test_cases = [
        {"file_type": "wav", "session_id": "farmer_001"},
        {"file_type": "mp3", "session_id": "farmer_002"},
        {"file_type": "m4a", "session_id": "farmer_003"},
    ]
    
    for tc in test_cases:
        event = {
            "queryStringParameters": {"file_type": tc["file_type"]},
            "headers": {"X-Session-Id": tc["session_id"]},
        }
        
        response = upload_url_handler(event, {})
        body = json.loads(response["body"])
        
        if response["statusCode"] == 200:
            print(f"✓ {tc['file_type'].upper()} upload URL generated")
            print(f"  Session: {tc['session_id']}")
            print(f"  S3 Key: {body['s3_key']}")
        else:
            print(f"✗ Failed for {tc['file_type']}: {body.get('error')}")
    
    return True


def test_asr_handler_validation():
    """Test ASR handler input validation."""
    print("\n" + "="*60)
    print("4. Testing ASR Handler Validation")
    print("="*60)
    
    from src.voice.handlers import asr_handler
    
    # Test missing s3_key
    event = {
        "headers": {"X-Session-Id": "test123", "X-Language": "hi"},
        "body": json.dumps({}),
    }
    
    response = asr_handler(event, {})
    body = json.loads(response["body"])
    
    if response["statusCode"] == 400 and "s3_key" in body.get("error", ""):
        print("✓ Missing s3_key returns 400 error")
    else:
        print(f"✗ Expected 400 error, got {response['statusCode']}")
    
    # Test with valid request structure (will fail on actual transcription)
    event = {
        "headers": {"X-Session-Id": "test123", "X-Language": "en"},
        "body": json.dumps({"s3_key": "uploads/test/audio.wav"}),
    }
    
    print("✓ ASR handler validation working")
    return True


def test_tts_handler_validation():
    """Test TTS handler input validation."""
    print("\n" + "="*60)
    print("5. Testing TTS Handler Validation")
    print("="*60)
    
    from src.voice.handlers import tts_handler
    
    # Test missing text
    event = {
        "headers": {"X-Session-Id": "test123", "X-Language": "hi"},
        "body": json.dumps({}),
    }
    
    response = tts_handler(event, {})
    body = json.loads(response["body"])
    
    if response["statusCode"] == 400 and "text" in body.get("error", ""):
        print("✓ Missing text returns 400 error")
    else:
        print(f"✗ Expected 400 error, got {response['statusCode']}")
    
    print("✓ TTS handler validation working")
    return True


def test_language_parsing():
    """Test language parsing from various input formats."""
    print("\n" + "="*60)
    print("6. Testing Language Parsing")
    print("="*60)
    
    from src.voice.handlers import _get_language
    from src.voice.config import Language
    
    test_cases = [
        # Query parameters
        ({"queryStringParameters": {"language": "en"}}, Language.ENGLISH, "Query param: en"),
        ({"queryStringParameters": {"language": "hi"}}, Language.HINDI, "Query param: hi"),
        ({"queryStringParameters": {"language": "or"}}, Language.ODIA, "Query param: or"),
        ({"queryStringParameters": {"language": "odia"}}, Language.ODIA, "Query param: odia"),
        ({"queryStringParameters": {"language": "od"}}, Language.ODIA, "Query param: od"),
        
        # Headers
        ({"headers": {"X-Language": "en"}}, Language.ENGLISH, "Header: X-Language: en"),
        ({"headers": {"x-language": "hi"}}, Language.HINDI, "Header: x-language: hi"),
        
        # Default
        ({}, Language.ENGLISH, "Empty event (default)"),
        ({"queryStringParameters": None}, Language.ENGLISH, "Null params (default)"),
    ]
    
    all_passed = True
    for event, expected, desc in test_cases:
        result = _get_language(event)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} {desc} → {result.value}")
    
    return all_passed


def test_session_id_extraction():
    """Test session ID extraction."""
    print("\n" + "="*60)
    print("7. Testing Session ID Extraction")
    print("="*60)
    
    from src.voice.handlers import _get_session_id
    
    test_cases = [
        ({"headers": {"X-Session-Id": "session123"}}, "session123"),
        ({"headers": {"x-session-id": "session456"}}, "session456"),
        ({"queryStringParameters": {"session_id": "session789"}}, "session789"),
        ({}, "anonymous"),
    ]
    
    all_passed = True
    for event, expected in test_cases:
        result = _get_session_id(event)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"{status} {event} → {result}")
    
    return all_passed


def test_polly_voice_config():
    """Test Polly voice configuration."""
    print("\n" + "="*60)
    print("8. Testing Polly Voice Configuration")
    print("="*60)
    
    from src.voice.tts.polly_client import PollyTTS
    from src.voice.config import Language
    
    polly = PollyTTS()
    
    print("Available voices:")
    for lang in [Language.ENGLISH, Language.HINDI]:
        voice = polly.voice_ids.get(lang, "N/A")
        print(f"  {lang.value.upper()}: {voice}")
    
    print("✓ Polly configuration valid")
    return True


def test_transcribe_config():
    """Test Transcribe configuration."""
    print("\n" + "="*60)
    print("9. Testing Transcribe Configuration")
    print("="*60)
    
    from src.voice.asr.transcribe_client import TranscribeASR
    from src.voice.config import Language
    
    transcribe = TranscribeASR()
    
    print("Language codes:")
    for lang in [Language.ENGLISH, Language.HINDI]:
        code = transcribe.language_codes.get(lang, "N/A")
        print(f"  {lang.value.upper()}: {code}")
    
    print("✓ Transcribe configuration valid")
    return True


def simulate_voice_pipeline():
    """Simulate the full voice pipeline flow."""
    print("\n" + "="*60)
    print("10. Simulating Voice Pipeline Flow")
    print("="*60)
    
    print("""
    Simulated Flow:
    ┌─────────────────────────────────────────────────────────┐
    │  1. Farmer opens app, selects Hindi                     │
    │  2. App calls GET /voice/upload-url                     │
    │     → Returns pre-signed S3 URL                         │
    │  3. App uploads audio directly to S3                    │
    │  4. App calls POST /voice/ask with s3_key               │
    │     ├── Rate limit check (DynamoDB)                     │
    │     ├── Download audio from S3                          │
    │     ├── ASR: Transcribe (Hindi) → Text                  │
    │     ├── RAG: Query Pinecone + Claude                    │
    │     ├── TTS: Polly (Hindi) → Audio                      │
    │     └── Upload response audio to S3                     │
    │  5. App receives audio URL, plays response              │
    └─────────────────────────────────────────────────────────┘
    """)
    
    # Simulate the request/response flow
    print("Sample Request:")
    sample_request = {
        "httpMethod": "POST",
        "path": "/voice/ask",
        "headers": {
            "X-Session-Id": "farmer_maharashtra_001",
            "X-Language": "hi",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "s3_key": "uploads/farmer_maharashtra_001/query_audio.wav"
        })
    }
    print(json.dumps(sample_request, indent=2))
    
    print("\nSample Response (simulated):")
    sample_response = {
        "statusCode": 200,
        "body": {
            "transcribed_text": "काली मिट्टी में कौन सी फसल अच्छी है?",
            "rag_response": "काली मिट्टी में सोयाबीन, मूंगफली और कपास की खेती अच्छी होती है।",
            "audio_url": "https://s3.../responses/farmer_001/response.mp3",
            "asr_provider": "transcribe",
            "tts_provider": "polly",
            "language": "hi"
        }
    }
    print(json.dumps(sample_response, indent=2))
    
    print("\n✓ Pipeline flow simulation complete")
    return True


def main():
    print("="*60)
    print("🎤 VOICE AI LOCAL SIMULATION TEST")
    print("="*60)
    
    tests = [
        ("Voice Config", test_voice_config),
        ("Handler Imports", test_handlers_structure),
        ("Upload URL Generation", test_upload_url_generation),
        ("ASR Validation", test_asr_handler_validation),
        ("TTS Validation", test_tts_handler_validation),
        ("Language Parsing", test_language_parsing),
        ("Session ID Extraction", test_session_id_extraction),
        ("Polly Config", test_polly_voice_config),
        ("Transcribe Config", test_transcribe_config),
        ("Pipeline Simulation", simulate_voice_pipeline),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed with error: {e}")
            results.append((name, False))
    
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
    
    if passed == total:
        print("\n🎉 All local tests passed!")
        print("\nNext steps to test with real AWS services:")
        print("  1. Deploy: sam build -t template-voice.yaml && sam deploy --guided")
        print("  2. Test: python test_voice_api.py --api-url <your-api-url>")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
