# Voice AI Architecture Documentation
## Multilingual ASR + TTS for Farmer RAG System

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FARMER VOICE AI SYSTEM                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

    FARMER (Mobile App)
           │
           ├── 1. Select Language (EN/HI/OR)
           ├── 2. Get Upload URL
           ├── 3. Upload Audio to S3
           ├── 4. Call /voice/ask
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│  GET  /ask                    → Existing RAG (text-only)                        │
│  GET  /voice/upload-url       → Pre-signed S3 URL                               │
│  POST /voice/asr              → Speech-to-Text only                             │
│  POST /voice/tts              → Text-to-Speech only                             │
│  POST /voice/ask              → Full Pipeline (ASR→RAG→TTS)                     │
│  GET  /voice/rate-limit-status → Check remaining requests                       │
└─────────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              LAMBDA LAYER                                        │
├────────────────┬────────────────┬────────────────┬─────────────────────────────┤
│  Upload URL    │  ASR Router    │  TTS Router    │  Full Pipeline              │
│  Lambda        │  Lambda        │  Lambda        │  Lambda                     │
├────────────────┴────────────────┴────────────────┴─────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         RATE LIMITER                                     │   │
│  │  • Check DynamoDB for session limits                                    │   │
│  │  • 5 requests/hour per session                                          │   │
│  │  • Returns 429 if exceeded                                              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐           │
│  │      ASR ROUTING             │  │      TTS ROUTING             │           │
│  ├──────────────────────────────┤  ├──────────────────────────────┤           │
│  │  EN/HI → AWS Transcribe      │  │  EN/HI → AWS Polly           │           │
│  │  Odia  → OpenAI Whisper      │  │  Odia  → OpenAI TTS          │           │
│  └──────────────────────────────┘  └──────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         EXISTING RAG PIPELINE                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   Titan     │───▶│  Pinecone   │───▶│   Prompt    │───▶│   Claude    │      │
│  │ Embeddings  │    │   Search    │    │  Builder    │    │   LLM       │      │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘      │
└─────────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STORAGE LAYER                                          │
├──────────────────────────┬──────────────────────────────────────────────────────┤
│  S3 (Audio Files)        │  DynamoDB (Rate Limits)                              │
│  ├── uploads/            │  ┌────────────────────────────────────────────────┐  │
│  │   └── {session}/      │  │ pk: "{session}#asr"                            │  │
│  ├── responses/          │  │ request_count: 3                               │  │
│  │   └── {session}/      │  │ window_start: 1704067200                       │  │
│  └── temp/               │  │ ttl: 1704074400 (auto-delete)                  │  │
│  (Lifecycle: 1 day)      │  └────────────────────────────────────────────────┘  │
└──────────────────────────┴──────────────────────────────────────────────────────┘
```

---

## 2. Data Flow: Full Voice Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    VOICE PIPELINE SEQUENCE DIAGRAM                            │
└──────────────────────────────────────────────────────────────────────────────┘

  Farmer App              API Gateway           Lambda              Services
      │                       │                    │                    │
      │  1. GET /voice/upload-url                  │                    │
      │─────────────────────▶│                    │                    │
      │                       │──────────────────▶│                    │
      │                       │                    │─── Generate ─────▶│ S3
      │                       │                    │◀── Pre-signed URL─│
      │◀──────────────────────│◀─────────────────│                    │
      │  {upload_url, s3_key}                      │                    │
      │                       │                    │                    │
      │  2. PUT audio to S3 (direct)               │                    │
      │───────────────────────────────────────────────────────────────▶│ S3
      │◀──────────────────────────────────────────────────────────────│
      │  200 OK                                    │                    │
      │                       │                    │                    │
      │  3. POST /voice/ask {s3_key, language}     │                    │
      │─────────────────────▶│                    │                    │
      │                       │──────────────────▶│                    │
      │                       │                    │                    │
      │                       │                    │── Check Rate ────▶│ DynamoDB
      │                       │                    │◀─ Allowed (3/5) ──│
      │                       │                    │                    │
      │                       │                    │── Get Audio ─────▶│ S3
      │                       │                    │◀─ audio_bytes ────│
      │                       │                    │                    │
      │                       │                    │── Transcribe ────▶│ Transcribe/
      │                       │                    │◀─ "crops query" ──│ Whisper
      │                       │                    │                    │
      │                       │                    │── RAG Query ─────▶│ RAG Pipeline
      │                       │                    │◀─ "wheat, rice" ──│
      │                       │                    │                    │
      │                       │                    │── Synthesize ────▶│ Polly/
      │                       │                    │◀─ audio_bytes ────│ OpenAI TTS
      │                       │                    │                    │
      │                       │                    │── Upload Audio ──▶│ S3
      │                       │                    │◀─ s3_key ─────────│
      │                       │                    │                    │
      │◀──────────────────────│◀─────────────────│                    │
      │  {transcribed_text,                       │                    │
      │   rag_response,                           │                    │
      │   audio_url}                              │                    │
      │                       │                    │                    │
      │  4. GET audio (pre-signed URL)             │                    │
      │───────────────────────────────────────────────────────────────▶│ S3
      │◀──────────────────────────────────────────────────────────────│
      │  audio/mpeg                               │                    │
```

---

## 3. DynamoDB Schema for Rate Limiting

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  TABLE: farmer-voice-rate-limits                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  Primary Key:                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │  pk (Partition Key): String                                                 ││
│  │  Format: "{session_id}#{request_type}"                                      ││
│  │  Example: "user_abc123#asr" or "user_abc123#tts"                            ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  Attributes:                                                                     │
│  ┌────────────────────┬─────────┬───────────────────────────────────────────────┐
│  │  Attribute         │  Type   │  Description                                  │
│  ├────────────────────┼─────────┼───────────────────────────────────────────────┤
│  │  pk                │  S      │  Partition key (session#type)                 │
│  │  session_id        │  S      │  User/session identifier                      │
│  │  request_type      │  S      │  "asr" or "tts"                               │
│  │  request_count     │  N      │  Number of requests in current window         │
│  │  window_start      │  N      │  Unix timestamp when window started           │
│  │  last_request      │  N      │  Unix timestamp of last request               │
│  │  ttl               │  N      │  TTL for auto-deletion (window_start + 3900)  │
│  └────────────────────┴─────────┴───────────────────────────────────────────────┘
│                                                                                  │
│  TTL Configuration:                                                              │
│  • Attribute: ttl                                                                │
│  • Value: window_start + 3900 seconds (1 hour + 5 min buffer)                   │
│  • DynamoDB auto-deletes expired items                                          │
│                                                                                  │
│  Example Item:                                                                   │
│  {                                                                               │
│    "pk": "farmer_session_xyz#asr",                                              │
│    "session_id": "farmer_session_xyz",                                          │
│    "request_type": "asr",                                                       │
│    "request_count": 3,                                                          │
│    "window_start": 1704067200,                                                  │
│    "last_request": 1704068500,                                                  │
│    "ttl": 1704071100                                                            │
│  }                                                                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. API Endpoints Reference

### 4.1 Get Upload URL
```
GET /voice/upload-url?language=hi&file_type=wav

Headers:
  X-Session-Id: farmer_session_123

Response:
{
  "upload_url": "https://s3.ap-south-1.amazonaws.com/farmer-voice.../presigned",
  "s3_key": "uploads/farmer_session_123/abc123.wav",
  "expires_in": 300,
  "content_type": "audio/wav"
}
```

### 4.2 ASR (Speech-to-Text)
```
POST /voice/asr

Headers:
  X-Session-Id: farmer_session_123
  X-Language: hi

Body:
{
  "s3_key": "uploads/farmer_session_123/abc123.wav",
  "query_rag": false
}

Response:
{
  "text": "कौन सी फसल अच्छी है",
  "provider": "transcribe",
  "language": "hi",
  "success": true,
  "rate_limit": {
    "remaining": 4,
    "reset_in_seconds": 3200
  }
}
```

### 4.3 TTS (Text-to-Speech)
```
POST /voice/tts

Headers:
  X-Session-Id: farmer_session_123
  X-Language: or

Body:
{
  "text": "ଧାନ ଏବଂ ଚାଉଳ ଭଲ ଫସଲ",
  "return_url": true
}

Response:
{
  "audio_url": "https://s3.../presigned-download-url",
  "provider": "openai",
  "language": "or",
  "success": true,
  "rate_limit": {
    "remaining": 3,
    "reset_in_seconds": 2800
  }
}
```

### 4.4 Full Voice Pipeline
```
POST /voice/ask

Headers:
  X-Session-Id: farmer_session_123
  X-Language: hi

Body:
{
  "s3_key": "uploads/farmer_session_123/abc123.wav"
}

Response:
{
  "transcribed_text": "कौन सी फसल मिट्टी के लिए अच्छी है",
  "rag_response": "Based on the soil type, wheat and rice are recommended...",
  "audio_url": "https://s3.../response-audio.mp3",
  "asr_provider": "transcribe",
  "tts_provider": "polly",
  "language": "hi"
}
```

### 4.5 Rate Limit Status
```
GET /voice/rate-limit-status

Headers:
  X-Session-Id: farmer_session_123

Response:
{
  "session_id": "farmer_session_123",
  "max_requests_per_hour": 5,
  "asr": {
    "allowed": true,
    "remaining": 3,
    "reset_in_seconds": 1800,
    "current_count": 2
  },
  "tts": {
    "allowed": true,
    "remaining": 4,
    "reset_in_seconds": 1800,
    "current_count": 1
  }
}
```

---

## 5. Routing Logic

### 5.1 ASR Router Pseudocode
```python
def route_asr(audio_s3_key: str, language: str, session_id: str):
    # 1. Check rate limit
    if not rate_limiter.check(session_id, "asr"):
        raise RateLimitExceeded()
    
    # 2. Route based on language
    if language in ["en", "hi"]:
        # AWS Transcribe for English/Hindi
        provider = "transcribe"
        text = transcribe_client.transcribe(
            s3_uri=f"s3://{bucket}/{audio_s3_key}",
            language_code="en-IN" if language == "en" else "hi-IN"
        )
    elif language == "or":
        # OpenAI Whisper for Odia
        provider = "whisper"
        audio_bytes = s3.get_object(audio_s3_key)
        text = whisper_client.transcribe(
            audio=audio_bytes,
            language="or"
        )
    
    # 3. Cleanup source audio
    s3.delete_object(audio_s3_key)
    
    # 4. Increment rate limit counter
    rate_limiter.increment(session_id, "asr")
    
    return {"text": text, "provider": provider}
```

### 5.2 TTS Router Pseudocode
```python
def route_tts(text: str, language: str, session_id: str):
    # 1. Check rate limit
    if not rate_limiter.check(session_id, "tts"):
        raise RateLimitExceeded()
    
    # 2. Route based on language
    if language in ["en", "hi"]:
        # AWS Polly for English/Hindi
        provider = "polly"
        audio_bytes = polly_client.synthesize(
            text=text,
            voice_id="Aditi",
            language_code="en-IN" if language == "en" else "hi-IN"
        )
    elif language == "or":
        # OpenAI TTS for Odia
        provider = "openai"
        audio_bytes = openai_tts.synthesize(
            text=text,
            voice="alloy",
            model="tts-1"
        )
    
    # 3. Upload to S3 and get download URL
    s3_key = s3.upload(audio_bytes, f"responses/{session_id}/")
    download_url = s3.generate_presigned_url(s3_key)
    
    # 4. Increment rate limit counter
    rate_limiter.increment(session_id, "tts")
    
    return {"audio_url": download_url, "provider": provider}
```

---

## 6. Best Practices

### 6.1 Security
```
✅ DO:
  • Use pre-signed URLs (expire in 5 min)
  • Validate session IDs
  • Store API keys in AWS Secrets Manager / SSM Parameter Store
  • Enable S3 bucket encryption (SSE-S3)
  • Block public S3 access
  • Use IAM roles with least privilege

❌ DON'T:
  • Accept raw audio in Lambda payload
  • Store OpenAI keys in environment variables (use Secrets Manager)
  • Allow public S3 bucket access
```

### 6.2 Cost Control
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SERVICE              │  COST FACTOR           │  OPTIMIZATION                  │
├───────────────────────┼────────────────────────┼────────────────────────────────┤
│  Amazon Transcribe    │  $0.024/min            │  Short audio (5-15s)           │
│  Amazon Polly         │  $4/1M chars (Neural)  │  Use Standard where possible   │
│  OpenAI Whisper       │  $0.006/min            │  Only for Odia                 │
│  OpenAI TTS           │  $15/1M chars          │  Only for Odia                 │
│  DynamoDB             │  Pay-per-request       │  TTL cleanup                   │
│  S3                   │  Storage + requests    │  Lifecycle rules               │
│  Lambda               │  Duration + memory     │  Right-size memory             │
└───────────────────────┴────────────────────────┴────────────────────────────────┘

Rate Limiting Savings:
  • 5 requests/hour/session limits abuse
  • Estimated max cost: ~$0.05/session/hour
```

### 6.3 Error Handling
```python
# Standard error response format
def error_response(status_code: int, error: str, details: dict = None):
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "error": error,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
    }

# Error codes
400 - Bad Request (missing s3_key, invalid language)
401 - Unauthorized (invalid session)
429 - Rate Limit Exceeded (include Retry-After header)
500 - Internal Server Error
502 - Service Error (Transcribe/Polly/OpenAI failure)
```

### 6.4 Observability
```yaml
CloudWatch Metrics to Track:
  - ASRRequestCount (by language, provider)
  - TTSRequestCount (by language, provider)
  - ASRLatency (P50, P95, P99)
  - TTSLatency (P50, P95, P99)
  - RateLimitHits
  - ErrorCount (by error type)

CloudWatch Alarms:
  - High error rate (> 5% in 5 min)
  - High latency (P95 > 10s)
  - Rate limit abuse (> 100 429s/hour)

Logging:
  - Structured JSON logs
  - Request IDs for tracing
  - Sensitive data redaction
```

---

## 7. Deployment Commands

```bash
# Build and deploy
sam build -t template-voice.yaml
sam deploy --guided

# Deploy with parameters
sam deploy \
  --template-file template-voice.yaml \
  --stack-name farmer-rag-voice \
  --parameter-overrides \
    PineconeApiKey=your-pinecone-key \
    OpenAIApiKey=your-openai-key \
    MaxRequestsPerHour=5 \
  --capabilities CAPABILITY_IAM

# Test endpoints
# 1. Get upload URL
curl "https://xxx.execute-api.ap-south-1.amazonaws.com/Prod/voice/upload-url?file_type=wav" \
  -H "X-Session-Id: test123"

# 2. Upload audio (using the returned upload_url)
curl -X PUT "PRESIGNED_UPLOAD_URL" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav

# 3. Transcribe
curl -X POST "https://xxx.execute-api.ap-south-1.amazonaws.com/Prod/voice/asr" \
  -H "X-Session-Id: test123" \
  -H "X-Language: hi" \
  -H "Content-Type: application/json" \
  -d '{"s3_key": "uploads/test123/abc.wav"}'
```

---

## 8. File Structure

```
src/
├── handler.py              # Existing RAG handler (unchanged)
├── config.py               # Existing config
├── voice/                  # NEW: Voice AI module
│   ├── __init__.py
│   ├── config.py           # Voice config (languages, providers)
│   ├── handlers.py         # Lambda handlers for voice endpoints
│   ├── rate_limiter.py     # DynamoDB rate limiting
│   ├── s3_manager.py       # S3 operations for audio
│   ├── asr/
│   │   ├── __init__.py
│   │   ├── router.py       # ASR routing logic
│   │   ├── transcribe_client.py  # AWS Transcribe
│   │   └── whisper_client.py     # OpenAI Whisper
│   └── tts/
│       ├── __init__.py
│       ├── router.py       # TTS routing logic
│       ├── polly_client.py       # AWS Polly
│       └── openai_client.py      # OpenAI TTS
├── embeddings/             # Existing
├── ingestion/              # Existing
├── llm/                    # Existing
├── rag/                    # Existing
└── utils/                  # Existing
```

---

## 9. Future Enhancements

1. **Translation Layer**: Add translation for non-English queries before RAG
2. **Streaming ASR**: Use WebSocket for real-time transcription
3. **Voice Activity Detection**: Skip silence in audio
4. **Caching**: Cache common TTS responses
5. **Analytics**: Track usage patterns by region/language
