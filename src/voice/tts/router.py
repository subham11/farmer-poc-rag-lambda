"""
TTS Router
----------
Routes TTS requests to appropriate provider based on language.
"""

import logging
from typing import Optional
from ..config import Language, TTSProvider, get_tts_provider, config
from ..s3_manager import s3_manager
from .polly_client import PollyTTS
from .openai_client import OpenAITTS

# Setup logger (compatible with both local and Lambda)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TTSRouter:
    """
    Routes TTS requests to the appropriate provider.
    
    Routing Logic:
    - English (EN) → Amazon Polly
    - Hindi (HI) → Amazon Polly
    - Odia (OR) → OpenAI TTS
    """
    
    def __init__(self):
        self._polly: Optional[PollyTTS] = None
        self._openai: Optional[OpenAITTS] = None
    
    @property
    def polly(self) -> PollyTTS:
        """Lazy initialization of Polly client."""
        if self._polly is None:
            self._polly = PollyTTS()
        return self._polly
    
    @property
    def openai_tts(self) -> OpenAITTS:
        """Lazy initialization of OpenAI TTS client."""
        if self._openai is None:
            self._openai = OpenAITTS()
        return self._openai
    
    def synthesize_speech(
        self,
        text: str,
        language: Language,
        session_id: str,
        save_to_s3: bool = True
    ) -> dict:
        """
        Convert text to speech using the appropriate provider.
        
        Args:
            text: Text to convert to speech
            language: Target language for speech
            session_id: Session identifier
            save_to_s3: Whether to save audio to S3 and return URL
        
        Returns:
            dict with keys: audio_url, audio_bytes (if not saved), provider, language
        """
        provider = get_tts_provider(language)
        
        logger.info(
            f"TTS routing: language={language.value}, "
            f"provider={provider.value}, session={session_id}"
        )
        
        try:
            if provider == TTSProvider.POLLY:
                audio_bytes = self.polly.synthesize(text, language)
            elif provider == TTSProvider.OPENAI:
                audio_bytes = self.openai_tts.synthesize(text, language)
            else:
                raise ValueError(f"Unknown TTS provider: {provider}")
            
            result = {
                "provider": provider.value,
                "language": language.value,
                "success": True,
                "text_length": len(text),
                "audio_size": len(audio_bytes),
            }
            
            if save_to_s3:
                # Upload to S3 and generate download URL
                s3_key = s3_manager.upload_audio(
                    audio_bytes,
                    session_id,
                    prefix="responses",
                    file_extension="mp3",
                    content_type="audio/mpeg"
                )
                download_url = s3_manager.generate_download_url(s3_key, expiry=300)
                
                result["audio_url"] = download_url
                result["s3_key"] = s3_key
            else:
                # Return audio bytes directly (base64 encoded for JSON)
                import base64
                result["audio_base64"] = base64.b64encode(audio_bytes).decode('utf-8')
            
            return result
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise
    
    def synthesize_to_bytes(
        self,
        text: str,
        language: Language
    ) -> bytes:
        """
        Simple method to get audio bytes directly.
        
        Args:
            text: Text to convert
            language: Target language
        
        Returns:
            Audio bytes
        """
        provider = get_tts_provider(language)
        
        if provider == TTSProvider.POLLY:
            return self.polly.synthesize(text, language)
        elif provider == TTSProvider.OPENAI:
            return self.openai_tts.synthesize(text, language)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")


# Singleton instance
tts_router = TTSRouter()
