"""
ASR Router
----------
Routes ASR requests to appropriate provider based on language.
"""

import logging
from typing import Optional
from ..config import Language, ASRProvider, get_asr_provider, config
from ..s3_manager import s3_manager
from .transcribe_client import TranscribeASR
from .whisper_client import WhisperASR

# Setup logger (compatible with both local and Lambda)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ASRRouter:
    """
    Routes ASR requests to the appropriate provider.
    
    Routing Logic:
    - English (EN) → Amazon Transcribe
    - Hindi (HI) → Amazon Transcribe
    - Odia (OR) → OpenAI Whisper
    """
    
    def __init__(self):
        self._transcribe: Optional[TranscribeASR] = None
        self._whisper: Optional[WhisperASR] = None
    
    @property
    def transcribe(self) -> TranscribeASR:
        """Lazy initialization of Transcribe client."""
        if self._transcribe is None:
            self._transcribe = TranscribeASR()
        return self._transcribe
    
    @property
    def whisper(self) -> WhisperASR:
        """Lazy initialization of Whisper client."""
        if self._whisper is None:
            self._whisper = WhisperASR()
        return self._whisper
    
    def transcribe_audio(
        self,
        s3_key: str,
        language: Language,
        session_id: str
    ) -> dict:
        """
        Transcribe audio from S3 using the appropriate provider.
        
        Args:
            s3_key: S3 object key for uploaded audio
            language: User-selected language
            session_id: Session identifier
        
        Returns:
            dict with keys: text, provider, language
        """
        provider = get_asr_provider(language)
        
        logger.info(
            f"ASR routing: language={language.value}, "
            f"provider={provider.value}, session={session_id}"
        )
        
        try:
            if provider == ASRProvider.TRANSCRIBE:
                text = self.transcribe.transcribe_from_s3(s3_key, language)
            elif provider == ASRProvider.WHISPER:
                text = self.whisper.transcribe_from_s3(s3_manager, s3_key, language)
            else:
                raise ValueError(f"Unknown ASR provider: {provider}")
            
            # Cleanup source audio after successful transcription
            s3_manager.delete_audio(s3_key)
            
            return {
                "text": text,
                "provider": provider.value,
                "language": language.value,
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"ASR error: {e}")
            # Still try to cleanup
            s3_manager.delete_audio(s3_key)
            raise
    
    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        language: Language,
        session_id: str
    ) -> dict:
        """
        Transcribe audio from bytes directly.
        
        Args:
            audio_bytes: Audio content as bytes
            language: User-selected language
            session_id: Session identifier
        
        Returns:
            dict with keys: text, provider, language
        """
        provider = get_asr_provider(language)
        
        logger.info(
            f"ASR routing (bytes): language={language.value}, "
            f"provider={provider.value}, session={session_id}"
        )
        
        try:
            if provider == ASRProvider.TRANSCRIBE:
                text = self.transcribe.transcribe_from_bytes(
                    audio_bytes, language, session_id
                )
            elif provider == ASRProvider.WHISPER:
                text = self.whisper.transcribe(audio_bytes, language)
            else:
                raise ValueError(f"Unknown ASR provider: {provider}")
            
            return {
                "text": text,
                "provider": provider.value,
                "language": language.value,
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"ASR error: {e}")
            raise


# Singleton instance
asr_router = ASRRouter()
