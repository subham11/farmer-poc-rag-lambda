"""
OpenAI TTS Client
-----------------
TTS for Odia using OpenAI TTS API.
"""

import json
import urllib.request
import urllib.error
import logging
from typing import Optional
from ..config import config, Language

# Setup logger (compatible with both local and Lambda)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class OpenAITTS:
    """
    OpenAI TTS API wrapper for Odia text-to-speech.
    
    Available voices: alloy, echo, fable, onyx, nova, shimmer
    Models: tts-1 (faster), tts-1-hd (higher quality)
    """
    
    TTS_API_URL = "https://api.openai.com/v1/audio/speech"
    
    def __init__(self):
        self.api_key = config.openai_api_key
        self.model = config.openai_tts_model
        self.default_voice = config.openai_tts_voice
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
    
    def synthesize(
        self,
        text: str,
        language: Language = Language.ODIA,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        response_format: str = "mp3"
    ) -> bytes:
        """
        Convert text to speech using OpenAI TTS.
        
        Args:
            text: Text to convert to speech
            language: Target language (for logging/metrics)
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: Model to use (tts-1 or tts-1-hd)
            response_format: Output format (mp3, opus, aac, flac)
        
        Returns:
            Audio content as bytes
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        voice = voice or self.default_voice
        model = model or self.model
        
        logger.info(f"Synthesizing speech with OpenAI: voice={voice}, model={model}")
        
        try:
            payload = json.dumps({
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": response_format,
            }).encode('utf-8')
            
            request = urllib.request.Request(
                self.TTS_API_URL,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
            )
            
            with urllib.request.urlopen(request, timeout=30) as response:
                audio_bytes = response.read()
            
            logger.info(f"OpenAI TTS complete: {len(audio_bytes)} bytes")
            
            return audio_bytes
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"OpenAI TTS error: {e.code} - {error_body}")
            raise Exception(f"OpenAI TTS error: {e.code}")
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise
    
    def synthesize_long_text(
        self,
        text: str,
        language: Language = Language.ODIA,
        voice: Optional[str] = None,
        max_chunk_length: int = 4000
    ) -> bytes:
        """
        Synthesize long text by chunking (OpenAI has 4096 char limit).
        
        Args:
            text: Long text to convert
            language: Target language
            voice: Voice to use
            max_chunk_length: Maximum characters per chunk
        
        Returns:
            Combined audio as bytes
        """
        if len(text) <= max_chunk_length:
            return self.synthesize(text, language, voice)
        
        # Split text into chunks at sentence boundaries
        chunks = self._split_text(text, max_chunk_length)
        audio_parts = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Synthesizing chunk {i+1}/{len(chunks)}")
            audio_bytes = self.synthesize(chunk, language, voice)
            audio_parts.append(audio_bytes)
        
        # For MP3, we can simply concatenate
        # Note: For production, use proper audio concatenation library
        return b''.join(audio_parts)
    
    def _split_text(self, text: str, max_length: int) -> list:
        """Split text into chunks at sentence boundaries."""
        sentences = text.replace('।', '.').replace('?', '?.').replace('!', '!.').split('.')
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) + 2 <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
