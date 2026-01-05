"""
OpenAI Whisper Client
---------------------
ASR for Odia using OpenAI Whisper API.
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


class WhisperASR:
    """
    OpenAI Whisper API wrapper for Odia speech-to-text.
    
    Note: Using urllib to avoid additional dependencies.
    For production, consider using the official openai package.
    """
    
    WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"
    
    def __init__(self):
        self.api_key = config.openai_api_key
        self.model = config.whisper_model
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
    
    def transcribe(
        self, 
        audio_bytes: bytes, 
        language: Language = Language.ODIA,
        filename: str = "audio.wav"
    ) -> str:
        """
        Transcribe audio using OpenAI Whisper.
        
        Args:
            audio_bytes: Audio content as bytes
            language: Language hint (defaults to Odia)
            filename: Filename hint for audio format
        
        Returns:
            Transcribed text
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Map language to ISO code for Whisper
        language_map = {
            Language.ODIA: "or",
            Language.HINDI: "hi",
            Language.ENGLISH: "en",
        }
        lang_code = language_map.get(language, "or")
        
        logger.info(f"Calling Whisper API for {lang_code} transcription")
        
        try:
            # Build multipart form data
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            
            body = self._build_multipart_body(
                audio_bytes=audio_bytes,
                filename=filename,
                model=self.model,
                language=lang_code,
                boundary=boundary
            )
            
            # Make request
            request = urllib.request.Request(
                self.WHISPER_API_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                }
            )
            
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            transcript = result.get('text', '')
            logger.info(f"Whisper transcription complete: {len(transcript)} chars")
            
            return transcript
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            logger.error(f"Whisper API error: {e.code} - {error_body}")
            raise Exception(f"Whisper API error: {e.code}")
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise
    
    def transcribe_from_s3(
        self, 
        s3_manager, 
        s3_key: str, 
        language: Language = Language.ODIA
    ) -> str:
        """
        Transcribe audio from S3 using Whisper.
        
        Args:
            s3_manager: S3Manager instance
            s3_key: S3 object key
            language: Language hint
        
        Returns:
            Transcribed text
        """
        # Download audio from S3
        audio_bytes = s3_manager.get_audio_bytes(s3_key)
        
        # Get filename from key
        filename = s3_key.rsplit('/', 1)[-1]
        
        return self.transcribe(audio_bytes, language, filename)
    
    def _build_multipart_body(
        self,
        audio_bytes: bytes,
        filename: str,
        model: str,
        language: str,
        boundary: str
    ) -> bytes:
        """Build multipart/form-data body for Whisper API."""
        
        # Determine content type from filename
        ext = filename.rsplit('.', 1)[-1].lower()
        content_type_map = {
            'wav': 'audio/wav',
            'mp3': 'audio/mpeg',
            'mp4': 'audio/mp4',
            'm4a': 'audio/mp4',
            'webm': 'audio/webm',
            'ogg': 'audio/ogg',
        }
        content_type = content_type_map.get(ext, 'audio/wav')
        
        parts = []
        
        # File part
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
        parts.append(f'Content-Type: {content_type}\r\n\r\n'.encode())
        parts.append(audio_bytes)
        parts.append(b'\r\n')
        
        # Model part
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(b'Content-Disposition: form-data; name="model"\r\n\r\n')
        parts.append(model.encode())
        parts.append(b'\r\n')
        
        # Language part
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(b'Content-Disposition: form-data; name="language"\r\n\r\n')
        parts.append(language.encode())
        parts.append(b'\r\n')
        
        # Response format
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(b'Content-Disposition: form-data; name="response_format"\r\n\r\n')
        parts.append(b'json')
        parts.append(b'\r\n')
        
        # End boundary
        parts.append(f"--{boundary}--\r\n".encode())
        
        return b''.join(parts)
