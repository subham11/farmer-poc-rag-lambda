"""
Voice AI Configuration
----------------------
Central configuration for ASR/TTS routing and rate limiting.
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class Language(Enum):
    """Supported languages for voice processing."""
    ENGLISH = "en"
    HINDI = "hi"
    ODIA = "or"


class ASRProvider(Enum):
    """ASR service providers."""
    TRANSCRIBE = "transcribe"  # AWS Transcribe for EN/HI
    WHISPER = "whisper"        # OpenAI Whisper for Odia


class TTSProvider(Enum):
    """TTS service providers."""
    POLLY = "polly"           # AWS Polly for EN/HI
    OPENAI = "openai"         # OpenAI TTS for Odia


@dataclass
class VoiceConfig:
    """Voice AI configuration settings."""
    
    # AWS Settings
    aws_region: str = os.environ.get("AWS_REGION", "ap-south-1")
    
    # S3 Settings
    audio_bucket: str = os.environ.get("AUDIO_BUCKET", "farmer-voice-audio")
    upload_url_expiry: int = 300  # 5 minutes
    
    # Rate Limiting
    rate_limit_table: str = os.environ.get("RATE_LIMIT_TABLE", "farmer-voice-rate-limits")
    max_requests_per_hour: int = int(os.environ.get("MAX_REQUESTS_PER_HOUR", "5"))
    rate_limit_window_seconds: int = 3600  # 1 hour
    
    # Transcribe Settings (EN/HI)
    transcribe_language_codes: dict = None
    
    # Polly Settings (EN/HI)
    polly_voice_ids: dict = None
    
    # OpenAI Settings (Odia)
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    whisper_model: str = "whisper-1"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"
    
    # RAG Pipeline
    rag_api_url: str = os.environ.get("RAG_API_URL", "")
    
    def __post_init__(self):
        """Initialize language-specific settings."""
        self.transcribe_language_codes = {
            Language.ENGLISH: "en-IN",  # Indian English
            Language.HINDI: "hi-IN",
        }
        
        self.polly_voice_ids = {
            Language.ENGLISH: "Aditi",   # Indian English female
            Language.HINDI: "Aditi",     # Hindi female voice
        }


# ASR Routing Map
ASR_ROUTING = {
    Language.ENGLISH: ASRProvider.TRANSCRIBE,
    Language.HINDI: ASRProvider.TRANSCRIBE,
    Language.ODIA: ASRProvider.WHISPER,
}

# TTS Routing Map
TTS_ROUTING = {
    Language.ENGLISH: TTSProvider.POLLY,
    Language.HINDI: TTSProvider.POLLY,
    Language.ODIA: TTSProvider.OPENAI,
}


def get_asr_provider(language: Language) -> ASRProvider:
    """Get ASR provider for a given language."""
    return ASR_ROUTING.get(language, ASRProvider.TRANSCRIBE)


def get_tts_provider(language: Language) -> TTSProvider:
    """Get TTS provider for a given language."""
    return TTS_ROUTING.get(language, TTSProvider.POLLY)


# Global config instance
config = VoiceConfig()
