"""
Voice Lambda Handlers
---------------------
API Gateway Lambda handlers for Voice AI endpoints:
- /voice/upload-url: Get pre-signed URL for audio upload
- /voice/asr: Speech-to-text processing
- /voice/tts: Text-to-speech processing
"""

import json
import os
import logging
import urllib.request
from typing import Any, Dict

# Set environment variables before imports
os.environ.setdefault("AWS_REGION", "ap-south-1")

from .config import Language, config
from .rate_limiter import rate_limiter, RateLimitExceeded
from .s3_manager import s3_manager
from .asr.router import asr_router
from .tts.router import tts_router
from ..agents.orchestrator import orchestrate_query

# Setup logger (compatible with both local and Lambda)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _response(status_code: int, body: dict, headers: dict = None) -> dict:
    """Build API Gateway response."""
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Session-Id,X-Language",
    }
    if headers:
        default_headers.update(headers)
    
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body),
    }


def _get_language(event: dict) -> Language:
    """Extract and validate language from request."""
    # Check query params, headers, or body
    params = event.get("queryStringParameters") or {}
    headers = event.get("headers") or {}
    
    lang_code = (
        params.get("language") or 
        headers.get("X-Language") or 
        headers.get("x-language") or
        "en"
    ).lower()
    
    language_map = {
        "en": Language.ENGLISH,
        "english": Language.ENGLISH,
        "hi": Language.HINDI,
        "hindi": Language.HINDI,
        "or": Language.ODIA,
        "odia": Language.ODIA,
        "od": Language.ODIA,
    }
    
    return language_map.get(lang_code, Language.ENGLISH)


def _get_session_id(event: dict) -> str:
    """Extract session ID from request."""
    headers = event.get("headers") or {}
    params = event.get("queryStringParameters") or {}
    
    return (
        headers.get("X-Session-Id") or
        headers.get("x-session-id") or
        params.get("session_id") or
        "anonymous"
    )


# =============================================================================
# UPLOAD URL HANDLER
# =============================================================================

def upload_url_handler(event: dict, context: Any) -> dict:
    """
    Generate pre-signed URL for audio upload.
    
    GET /voice/upload-url?language=hi&file_type=wav
    
    Headers:
        X-Session-Id: User session identifier
    
    Returns:
        {
            "upload_url": "https://s3.../presigned-url",
            "s3_key": "uploads/session123/uuid.wav",
            "expires_in": 300
        }
    """
    try:
        session_id = _get_session_id(event)
        params = event.get("queryStringParameters") or {}
        
        file_type = params.get("file_type", "wav").lower()
        content_type_map = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "m4a": "audio/mp4",
            "webm": "audio/webm",
        }
        content_type = content_type_map.get(file_type, "audio/wav")
        
        logger.info(f"Generating upload URL for session={session_id}, type={file_type}")
        
        upload_url, s3_key = s3_manager.generate_upload_url(
            session_id=session_id,
            file_extension=file_type,
            content_type=content_type
        )
        
        return _response(200, {
            "upload_url": upload_url,
            "s3_key": s3_key,
            "expires_in": config.upload_url_expiry,
            "content_type": content_type,
        })
        
    except Exception as e:
        logger.error(f"Upload URL error: {e}")
        return _response(500, {"error": str(e)})


# =============================================================================
# ASR HANDLER (Speech-to-Text)
# =============================================================================

def asr_handler(event: dict, context: Any) -> dict:
    """
    Process speech-to-text request.
    
    POST /voice/asr
    
    Headers:
        X-Session-Id: User session identifier
        X-Language: Language code (en, hi, or)
    
    Body:
        {
            "s3_key": "uploads/session123/audio.wav",
            "query_agents": true  // Optional: also run multi-agent analysis
        }
    
    Returns:
        {
            "text": "Transcribed text",
            "provider": "transcribe" | "whisper",
            "language": "en" | "hi" | "or",
            "agent_response": {...} // If query_agents=true
        }
    """
    try:
        session_id = _get_session_id(event)
        language = _get_language(event)
        
        # Parse body
        body = json.loads(event.get("body", "{}"))
        s3_key = body.get("s3_key")
        query_agents = body.get("query_agents", False)
        
        if not s3_key:
            return _response(400, {"error": "s3_key is required"})
        
        # Check rate limit
        try:
            allowed, remaining, reset_in = rate_limiter.check_and_increment(
                session_id, "asr"
            )
        except RateLimitExceeded as e:
            return _response(429, {
                "error": "Rate limit exceeded",
                "retry_after_seconds": e.remaining_seconds,
                "message": f"Maximum {config.max_requests_per_hour} ASR requests per hour"
            }, {"Retry-After": str(e.remaining_seconds)})
        
        logger.info(f"ASR request: session={session_id}, language={language.value}, s3_key={s3_key}")
        
        # Transcribe audio
        result = asr_router.transcribe_audio(
            s3_key=s3_key,
            language=language,
            session_id=session_id
        )
        
        result["rate_limit"] = {
            "remaining": remaining,
            "reset_in_seconds": reset_in,
        }
        
        # Optionally run multi-agent analysis
        if query_agents and result.get("text"):
            agent_response = orchestrate_query(result["text"])
            result["agent_response"] = agent_response
        
        return _response(200, result)
        
    except RateLimitExceeded as e:
        return _response(429, {
            "error": "Rate limit exceeded",
            "retry_after_seconds": e.remaining_seconds,
        })
    except Exception as e:
        logger.error(f"ASR error: {e}")
        return _response(500, {"error": str(e)})


# =============================================================================
# TTS HANDLER (Text-to-Speech)
# =============================================================================

def tts_handler(event: dict, context: Any) -> dict:
    """
    Process text-to-speech request.
    
    POST /voice/tts
    
    Headers:
        X-Session-Id: User session identifier
        X-Language: Language code (en, hi, or)
    
    Body:
        {
            "text": "Text to convert to speech",
            "return_url": true  // Return S3 URL (default) or base64
        }
    
    Returns:
        {
            "audio_url": "https://s3.../presigned-url",  // If return_url=true
            "audio_base64": "...",  // If return_url=false
            "provider": "polly" | "openai",
            "language": "en" | "hi" | "or"
        }
    """
    try:
        session_id = _get_session_id(event)
        language = _get_language(event)
        
        # Parse body
        body = json.loads(event.get("body", "{}"))
        text = body.get("text", "")
        return_url = body.get("return_url", True)
        
        if not text:
            return _response(400, {"error": "text is required"})
        
        # Check rate limit
        try:
            allowed, remaining, reset_in = rate_limiter.check_and_increment(
                session_id, "tts"
            )
        except RateLimitExceeded as e:
            return _response(429, {
                "error": "Rate limit exceeded",
                "retry_after_seconds": e.remaining_seconds,
                "message": f"Maximum {config.max_requests_per_hour} TTS requests per hour"
            }, {"Retry-After": str(e.remaining_seconds)})
        
        logger.info(f"TTS request: session={session_id}, language={language.value}, text_length={len(text)}")
        
        # Synthesize speech
        result = tts_router.synthesize_speech(
            text=text,
            language=language,
            session_id=session_id,
            save_to_s3=return_url
        )
        
        result["rate_limit"] = {
            "remaining": remaining,
            "reset_in_seconds": reset_in,
        }
        
        return _response(200, result)
        
    except RateLimitExceeded as e:
        return _response(429, {
            "error": "Rate limit exceeded",
            "retry_after_seconds": e.remaining_seconds,
        })
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return _response(500, {"error": str(e)})


# =============================================================================
# FULL VOICE PIPELINE HANDLER (ASR → RAG → TTS)
# =============================================================================

def voice_pipeline_handler(event: dict, context: Any) -> dict:
    """
    Full voice pipeline: Speech → Text → RAG → Speech
    
    POST /voice/ask
    
    Headers:
        X-Session-Id: User session identifier
        X-Language: Language code (en, hi, or)
    
    Body:
        {
            "s3_key": "uploads/session123/audio.wav"
        }
    
    Returns:
        {
            "transcribed_text": "User's question",
            "rag_response": "Answer from RAG",
            "audio_url": "https://s3.../response-audio.mp3",
            "asr_provider": "transcribe" | "whisper",
            "tts_provider": "polly" | "openai"
        }
    """
    try:
        session_id = _get_session_id(event)
        language = _get_language(event)
        
        # Parse body
        body = json.loads(event.get("body", "{}"))
        s3_key = body.get("s3_key")
        
        if not s3_key:
            return _response(400, {"error": "s3_key is required"})
        
        # Check rate limits (counts as both ASR and TTS)
        try:
            rate_limiter.check_and_increment(session_id, "asr")
            rate_limiter.check_and_increment(session_id, "tts")
        except RateLimitExceeded as e:
            return _response(429, {
                "error": "Rate limit exceeded",
                "retry_after_seconds": e.remaining_seconds,
            })
        
        logger.info(f"Voice pipeline: session={session_id}, language={language.value}")
        
        # Step 1: ASR - Speech to Text
        asr_result = asr_router.transcribe_audio(
            s3_key=s3_key,
            language=language,
            session_id=session_id
        )
        transcribed_text = asr_result.get("text", "")
        
        if not transcribed_text:
            return _response(400, {"error": "Could not transcribe audio"})
        
        # Step 2: Query RAG pipeline (expects English)
        # For non-English, you might want to add translation here
        rag_response = _query_rag_pipeline(transcribed_text)
        
        # Step 3: TTS - Text to Speech
        tts_result = tts_router.synthesize_speech(
            text=rag_response,
            language=language,
            session_id=session_id,
            save_to_s3=True
        )
        
        return _response(200, {
            "transcribed_text": transcribed_text,
            "rag_response": rag_response,
            "audio_url": tts_result.get("audio_url"),
            "asr_provider": asr_result.get("provider"),
            "tts_provider": tts_result.get("provider"),
            "language": language.value,
        })
        
    except Exception as e:
        logger.error(f"Voice pipeline error: {e}")
        return _response(500, {"error": str(e)})


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _query_rag_pipeline(query: str) -> str:
    """
    Query the existing RAG pipeline.
    
    Uses the RAG_API_URL if set, otherwise calls handler directly.
    """
    try:
        # Option 1: Call via HTTP if API URL is configured
        if config.rag_api_url:
            encoded_query = urllib.parse.quote(query)
            url = f"{config.rag_api_url}?query={encoded_query}"
            
            req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8")
        
        # Option 2: Call handler directly (same Lambda deployment)
        try:
            from handler import lambda_handler
        except ImportError:
            # Fallback for local testing
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from handler import lambda_handler
        
        rag_event = {"queryStringParameters": {"query": query}}
        rag_response = lambda_handler(rag_event, {})
        
        return rag_response.get("body", "")
        
    except Exception as e:
        logger.error(f"RAG pipeline error: {e}")
        return f"Error querying knowledge base: {str(e)}"


# =============================================================================
# RATE LIMIT STATUS HANDLER
# =============================================================================

def rate_limit_status_handler(event: dict, context: Any) -> dict:
    """
    Get current rate limit status.
    
    GET /voice/rate-limit-status
    
    Headers:
        X-Session-Id: User session identifier
    
    Returns:
        {
            "asr": {"remaining": 3, "reset_in_seconds": 1800},
            "tts": {"remaining": 5, "reset_in_seconds": 0}
        }
    """
    try:
        session_id = _get_session_id(event)
        
        asr_status = rate_limiter.get_status(session_id, "asr")
        tts_status = rate_limiter.get_status(session_id, "tts")
        
        return _response(200, {
            "session_id": session_id,
            "max_requests_per_hour": config.max_requests_per_hour,
            "asr": asr_status,
            "tts": tts_status,
        })
        
    except Exception as e:
        logger.error(f"Rate limit status error: {e}")
        return _response(500, {"error": str(e)})
