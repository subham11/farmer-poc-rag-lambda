"""
Amazon Polly Client
-------------------
TTS for English and Hindi using AWS Polly.
"""

import boto3
import logging
from typing import Optional
from ..config import config, Language

# Setup logger (compatible with both local and Lambda)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PollyTTS:
    """
    Amazon Polly wrapper for English/Hindi text-to-speech.
    
    Voices used:
    - English (Indian): Aditi (female), Raveena (female)
    - Hindi: Aditi (female)
    """
    
    def __init__(self):
        self.client = boto3.client('polly', region_name=config.aws_region)
        self.voice_ids = config.polly_voice_ids
    
    def synthesize(
        self,
        text: str,
        language: Language,
        voice_id: Optional[str] = None,
        output_format: str = "mp3"
    ) -> bytes:
        """
        Convert text to speech using Amazon Polly.
        
        Args:
            text: Text to convert to speech
            language: Target language (ENGLISH or HINDI)
            voice_id: Optional specific voice ID (default from config)
            output_format: Audio format (mp3, ogg_vorbis, pcm)
        
        Returns:
            Audio content as bytes
        """
        if language not in self.voice_ids:
            raise ValueError(f"Language {language} not supported by Polly")
        
        # Get voice ID
        voice = voice_id or self.voice_ids[language]
        
        # Get language code for Polly
        language_code_map = {
            Language.ENGLISH: "en-IN",
            Language.HINDI: "hi-IN",
        }
        language_code = language_code_map[language]
        
        logger.info(f"Synthesizing speech: voice={voice}, language={language_code}")
        
        try:
            # Use standard engine - neural not supported for all Indian voices
            response = self.client.synthesize_speech(
                Text=text,
                TextType="text",
                OutputFormat=output_format,
                VoiceId=voice,
                LanguageCode=language_code,
                Engine="standard"
            )
            
            # Read audio stream
            audio_bytes = response['AudioStream'].read()
            
            logger.info(f"Polly synthesis complete: {len(audio_bytes)} bytes")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Polly synthesis error: {e}")
            raise
    
    def synthesize_ssml(
        self,
        ssml_text: str,
        language: Language,
        voice_id: Optional[str] = None,
        output_format: str = "mp3"
    ) -> bytes:
        """
        Convert SSML text to speech for more control over pronunciation.
        
        Args:
            ssml_text: SSML-formatted text
            language: Target language
            voice_id: Optional specific voice ID
            output_format: Audio format
        
        Returns:
            Audio content as bytes
        """
        voice = voice_id or self.voice_ids.get(language, "Aditi")
        
        language_code_map = {
            Language.ENGLISH: "en-IN",
            Language.HINDI: "hi-IN",
        }
        language_code = language_code_map.get(language, "en-IN")
        
        try:
            response = self.client.synthesize_speech(
                Text=ssml_text,
                TextType="ssml",
                OutputFormat=output_format,
                VoiceId=voice,
                LanguageCode=language_code,
            )
            
            return response['AudioStream'].read()
            
        except Exception as e:
            logger.error(f"Polly SSML synthesis error: {e}")
            raise
    
    def _supports_neural(self, voice_id: str) -> bool:
        """Check if voice supports neural engine."""
        # Aditi supports neural for Hindi
        neural_voices = ["Aditi"]
        return voice_id in neural_voices
    
    def list_available_voices(self, language_code: str = "hi-IN") -> list:
        """List available Polly voices for a language."""
        try:
            response = self.client.describe_voices(
                LanguageCode=language_code
            )
            return response.get('Voices', [])
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []
