"""
Rate Limiter using DynamoDB
---------------------------
Session-based rate limiting with TTL for automatic cleanup.
Limits: 2-5 ASR/TTS requests per hour per session.
"""

import time
import boto3
import logging
from botocore.exceptions import ClientError
from typing import Tuple, Optional
from .config import config

# Setup logger (compatible with both local and Lambda)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, remaining_seconds: int):
        self.remaining_seconds = remaining_seconds
        super().__init__(f"Rate limit exceeded. Try again in {remaining_seconds} seconds.")


class RateLimiter:
    """
    DynamoDB-based rate limiter with TTL.
    
    DynamoDB Schema:
    ----------------
    Table: farmer-voice-rate-limits
    
    Primary Key:
        - pk (String): "{session_id}#{request_type}"  
                       e.g., "user123#asr" or "user123#tts"
    
    Attributes:
        - request_count (Number): Number of requests in current window
        - window_start (Number): Unix timestamp when window started
        - ttl (Number): Unix timestamp for DynamoDB TTL auto-deletion
    
    GSI (optional for analytics):
        - None required for basic rate limiting
    """
    
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
        self.table = self.dynamodb.Table(config.rate_limit_table)
        self.max_requests = config.max_requests_per_hour
        self.window_seconds = config.rate_limit_window_seconds
    
    def _get_partition_key(self, session_id: str, request_type: str) -> str:
        """Generate partition key for rate limit record."""
        return f"{session_id}#{request_type}"
    
    def check_and_increment(
        self, 
        session_id: str, 
        request_type: str = "asr"
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit and increment counter if allowed.
        
        Args:
            session_id: Unique identifier for user/session
            request_type: "asr" or "tts"
        
        Returns:
            Tuple of (allowed: bool, remaining: int, reset_in_seconds: int)
        
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        pk = self._get_partition_key(session_id, request_type)
        current_time = int(time.time())
        window_start = current_time
        ttl_time = current_time + self.window_seconds + 300  # Extra 5 min buffer
        
        try:
            # Try to get existing record
            response = self.table.get_item(Key={"pk": pk})
            
            if "Item" in response:
                item = response["Item"]
                stored_window_start = int(item.get("window_start", 0))
                request_count = int(item.get("request_count", 0))
                
                # Check if we're still in the same window
                if current_time - stored_window_start < self.window_seconds:
                    # Same window - check limit
                    if request_count >= self.max_requests:
                        remaining_seconds = self.window_seconds - (current_time - stored_window_start)
                        logger.warning(
                            f"Rate limit exceeded for {session_id}/{request_type}. "
                            f"Count: {request_count}, Reset in: {remaining_seconds}s"
                        )
                        raise RateLimitExceeded(remaining_seconds)
                    
                    # Increment counter
                    new_count = request_count + 1
                    window_start = stored_window_start
                else:
                    # Window expired - start new window
                    new_count = 1
                    window_start = current_time
            else:
                # No existing record - start fresh
                new_count = 1
            
            # Update/create record
            self.table.put_item(
                Item={
                    "pk": pk,
                    "session_id": session_id,
                    "request_type": request_type,
                    "request_count": new_count,
                    "window_start": window_start,
                    "ttl": ttl_time,
                    "last_request": current_time,
                }
            )
            
            remaining = self.max_requests - new_count
            reset_in = self.window_seconds - (current_time - window_start)
            
            logger.info(
                f"Rate limit check passed for {session_id}/{request_type}. "
                f"Count: {new_count}/{self.max_requests}, Remaining: {remaining}"
            )
            
            return True, remaining, reset_in
            
        except RateLimitExceeded:
            raise
        except ClientError as e:
            logger.error(f"DynamoDB error in rate limiter: {e}")
            # Fail open - allow request but log error
            return True, self.max_requests - 1, self.window_seconds
    
    def get_status(self, session_id: str, request_type: str = "asr") -> dict:
        """
        Get current rate limit status without incrementing.
        
        Returns:
            dict with keys: allowed, remaining, reset_in_seconds, current_count
        """
        pk = self._get_partition_key(session_id, request_type)
        current_time = int(time.time())
        
        try:
            response = self.table.get_item(Key={"pk": pk})
            
            if "Item" not in response:
                return {
                    "allowed": True,
                    "remaining": self.max_requests,
                    "reset_in_seconds": 0,
                    "current_count": 0,
                }
            
            item = response["Item"]
            stored_window_start = int(item.get("window_start", 0))
            request_count = int(item.get("request_count", 0))
            
            # Check if window expired
            if current_time - stored_window_start >= self.window_seconds:
                return {
                    "allowed": True,
                    "remaining": self.max_requests,
                    "reset_in_seconds": 0,
                    "current_count": 0,
                }
            
            remaining = max(0, self.max_requests - request_count)
            reset_in = self.window_seconds - (current_time - stored_window_start)
            
            return {
                "allowed": remaining > 0,
                "remaining": remaining,
                "reset_in_seconds": reset_in,
                "current_count": request_count,
            }
            
        except ClientError as e:
            logger.error(f"DynamoDB error getting status: {e}")
            return {
                "allowed": True,
                "remaining": self.max_requests,
                "reset_in_seconds": 0,
                "current_count": 0,
                "error": str(e),
            }


# Singleton instance
rate_limiter = RateLimiter()
