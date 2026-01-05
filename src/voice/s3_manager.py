"""
S3 Manager for Voice Audio Files
---------------------------------
Handles pre-signed URL generation, audio upload/download, and cleanup.
"""

import boto3
import uuid
import logging
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Optional, Tuple
from .config import config

# Setup logger (compatible with both local and Lambda)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class S3Manager:
    """
    Manages audio file operations in S3.
    
    Bucket Structure:
    -----------------
    farmer-voice-audio/
    ├── uploads/          # User-uploaded audio for ASR
    │   └── {session_id}/{uuid}.wav
    ├── responses/        # TTS-generated audio responses
    │   └── {session_id}/{uuid}.mp3
    └── temp/             # Temporary processing files
        └── {uuid}.*
    
    All files have S3 lifecycle rules for automatic cleanup.
    """
    
    def __init__(self):
        # Configure S3 client with signature version for pre-signed URLs
        s3_config = Config(
            signature_version='s3v4',
            region_name=config.aws_region
        )
        self.s3_client = boto3.client('s3', config=s3_config)
        self.bucket = config.audio_bucket
    
    def generate_upload_url(
        self, 
        session_id: str, 
        file_extension: str = "wav",
        content_type: str = "audio/wav"
    ) -> Tuple[str, str]:
        """
        Generate a pre-signed URL for audio upload.
        
        Args:
            session_id: User/session identifier
            file_extension: Audio file extension (wav, mp3, m4a)
            content_type: MIME type for the upload
        
        Returns:
            Tuple of (pre_signed_url, s3_key)
        """
        file_id = str(uuid.uuid4())
        s3_key = f"uploads/{session_id}/{file_id}.{file_extension}"
        
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': s3_key,
                    'ContentType': content_type,
                },
                ExpiresIn=config.upload_url_expiry,
                HttpMethod='PUT'
            )
            
            logger.info(f"Generated upload URL for {s3_key}")
            return presigned_url, s3_key
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def generate_download_url(self, s3_key: str, expiry: int = 300) -> str:
        """
        Generate a pre-signed URL for downloading audio.
        
        Args:
            s3_key: S3 object key
            expiry: URL expiry time in seconds
        
        Returns:
            Pre-signed download URL
        """
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': s3_key,
                },
                ExpiresIn=expiry
            )
            
            logger.info(f"Generated download URL for {s3_key}")
            return presigned_url
            
        except ClientError as e:
            logger.error(f"Error generating download URL: {e}")
            raise
    
    def get_audio_bytes(self, s3_key: str) -> bytes:
        """
        Download audio file content as bytes.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            Audio file content as bytes
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            audio_bytes = response['Body'].read()
            logger.info(f"Downloaded {len(audio_bytes)} bytes from {s3_key}")
            return audio_bytes
            
        except ClientError as e:
            logger.error(f"Error downloading audio from S3: {e}")
            raise
    
    def upload_audio(
        self, 
        audio_bytes: bytes, 
        session_id: str,
        prefix: str = "responses",
        file_extension: str = "mp3",
        content_type: str = "audio/mpeg"
    ) -> str:
        """
        Upload audio bytes to S3.
        
        Args:
            audio_bytes: Audio content as bytes
            session_id: User/session identifier
            prefix: S3 key prefix (uploads, responses, temp)
            file_extension: File extension
            content_type: MIME type
        
        Returns:
            S3 key of uploaded file
        """
        file_id = str(uuid.uuid4())
        s3_key = f"{prefix}/{session_id}/{file_id}.{file_extension}"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=audio_bytes,
                ContentType=content_type,
            )
            
            logger.info(f"Uploaded {len(audio_bytes)} bytes to {s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Error uploading audio to S3: {e}")
            raise
    
    def delete_audio(self, s3_key: str) -> bool:
        """
        Delete an audio file from S3.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            True if deleted successfully
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            logger.info(f"Deleted {s3_key} from S3")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting from S3: {e}")
            return False
    
    def check_file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False


# Singleton instance
s3_manager = S3Manager()
