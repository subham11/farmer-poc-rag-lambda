"""
Amazon Transcribe Client
------------------------
ASR for English and Hindi using AWS Transcribe.
"""

import boto3
import time
import uuid
import logging
from typing import Optional
from ..config import config, Language

# Setup logger (compatible with both local and Lambda)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TranscribeASR:
    """
    Amazon Transcribe wrapper for English/Hindi speech-to-text.
    
    Uses streaming transcription for short audio (5-15 seconds).
    Falls back to batch transcription if streaming unavailable.
    """
    
    def __init__(self):
        self.client = boto3.client('transcribe', region_name=config.aws_region)
        self.s3_client = boto3.client('s3', region_name=config.aws_region)
        self.bucket = config.audio_bucket
        self.language_codes = config.transcribe_language_codes
    
    def transcribe_from_s3(
        self, 
        s3_key: str, 
        language: Language,
        job_name: Optional[str] = None
    ) -> str:
        """
        Transcribe audio file from S3 using batch transcription.
        
        Args:
            s3_key: S3 object key for audio file
            language: Target language (ENGLISH or HINDI)
            job_name: Optional custom job name
        
        Returns:
            Transcribed text
        """
        if language not in self.language_codes:
            raise ValueError(f"Language {language} not supported by Transcribe")
        
        job_name = job_name or f"farmer-asr-{uuid.uuid4().hex[:8]}"
        language_code = self.language_codes[language]
        media_uri = f"s3://{self.bucket}/{s3_key}"
        
        logger.info(f"Starting Transcribe job: {job_name} for {language_code}")
        
        try:
            # Start transcription job
            self.client.start_transcription_job(
                TranscriptionJobName=job_name,
                LanguageCode=language_code,
                MediaFormat=self._get_media_format(s3_key),
                Media={'MediaFileUri': media_uri},
                Settings={
                    'ShowSpeakerLabels': False,
                    'ShowAlternatives': False,
                }
            )
            
            # Wait for completion (with timeout for short audio)
            transcript = self._wait_for_job(job_name, timeout=60)
            
            # Cleanup job
            self._cleanup_job(job_name)
            
            return transcript
            
        except Exception as e:
            logger.error(f"Transcribe error: {e}")
            self._cleanup_job(job_name)
            raise
    
    def transcribe_from_bytes(
        self, 
        audio_bytes: bytes, 
        language: Language,
        session_id: str
    ) -> str:
        """
        Transcribe audio from bytes by uploading to S3 first.
        
        Args:
            audio_bytes: Audio content as bytes
            language: Target language
            session_id: Session identifier for S3 path
        
        Returns:
            Transcribed text
        """
        # Upload to temp location
        temp_key = f"temp/{session_id}/{uuid.uuid4().hex}.wav"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=temp_key,
                Body=audio_bytes,
                ContentType='audio/wav'
            )
            
            # Transcribe from S3
            transcript = self.transcribe_from_s3(temp_key, language)
            
            return transcript
            
        finally:
            # Cleanup temp file
            try:
                self.s3_client.delete_object(Bucket=self.bucket, Key=temp_key)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")
    
    def _wait_for_job(self, job_name: str, timeout: int = 60) -> str:
        """Wait for transcription job to complete and return transcript."""
        start_time = time.time()
        
        while True:
            response = self.client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                # Get transcript from result
                transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                return self._fetch_transcript(transcript_uri)
            
            elif status == 'FAILED':
                failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown')
                raise Exception(f"Transcription failed: {failure_reason}")
            
            # Check timeout
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Transcription job timed out after {timeout}s")
            
            # Wait before polling again
            time.sleep(2)
    
    def _fetch_transcript(self, transcript_uri: str) -> str:
        """Fetch transcript text from result URI."""
        import urllib.request
        import json
        
        with urllib.request.urlopen(transcript_uri) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        transcripts = result.get('results', {}).get('transcripts', [])
        if transcripts:
            return transcripts[0].get('transcript', '')
        
        return ''
    
    def _get_media_format(self, s3_key: str) -> str:
        """Determine media format from file extension."""
        extension = s3_key.rsplit('.', 1)[-1].lower()
        format_map = {
            'wav': 'wav',
            'mp3': 'mp3',
            'mp4': 'mp4',
            'm4a': 'mp4',
            'flac': 'flac',
            'ogg': 'ogg',
            'webm': 'webm',
        }
        return format_map.get(extension, 'wav')
    
    def _cleanup_job(self, job_name: str):
        """Delete transcription job."""
        try:
            self.client.delete_transcription_job(TranscriptionJobName=job_name)
            logger.info(f"Cleaned up transcription job: {job_name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup job {job_name}: {e}")
