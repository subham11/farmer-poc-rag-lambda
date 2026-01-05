# Farmer RAG Backend Architecture with Swagger UI

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT / BROWSER                         │
│  (Swagger UI, Next.js Frontend, Postman, curl, etc.)            │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS Requests
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AWS API GATEWAY                             │
│                                                                 │
│  Routes:                                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ GET  /                   → SwaggerUILambda              │  │
│  │ GET  /openapi.json       → OpenAPISpecLambda           │  │
│  │ GET  /ask                → FarmerRAGLambda             │  │
│  │ POST /ask                → FarmerRAGLambda             │  │
│  │ POST /voice/upload-url   → VoiceUploadUrlLambda        │  │
│  │ POST /voice/asr          → VoiceASRLambda              │  │
│  │ POST /voice/tts          → VoiceTTSLambda              │  │
│  │ POST /voice/ask          → VoicePipelineLambda         │  │
│  └─────────────────────────────────────────────────────────┘  │
└────┬──────────────┬──────────────┬──────────────┬─────────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Swagger UI  │ │ RAG Lambda   │ │ Voice Lambda │ │ Voice Util   │
│  Lambda      │ │              │ │ Functions    │ │ Lambdas      │
│              │ │ • Retrieval  │ │              │ │              │
│ • Serves     │ │ • Prompt     │ │ • Upload URL │ │ • ASR        │
│   HTML UI    │ │ • LLM Call   │ │ • ASR        │ │ • TTS        │
│ • Serves     │ │              │ │ • TTS        │ │ • Pipeline   │
│   OpenAPI    │ │ ┌──────────┐ │ │ • Rate Limit │ │ • RateLimit  │
│   JSON       │ │ │Bedrock   │ │ │              │ │              │
│              │ │ │Claude 3  │ │ │ ┌──────────┐ │ │              │
│ ┌────────┐  │ │ │Haiku     │ │ │ │Bedrock   │ │ │              │
│ │  HTML  │  │ │ │LLM       │ │ │ │Transcribe│ │ │              │
│ │ Assets │  │ │ └──────────┘ │ │ │Polly     │ │ │              │
│ │  +CSS  │  │ │              │ │ │OpenAI    │ │ │              │
│ │   +JS  │  │ │              │ │ └──────────┘ │ │              │
│ └────────┘  │ │              │ │              │ │              │
│              │ │              │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                 │              │              │
                 ▼              ▼              ▼
           ┌─────────────────────────────────────────┐
           │         AWS SERVICES                    │
           │                                         │
           │ ┌─────────────────────────────────────┐ │
           │ │ AWS Bedrock (LLM Inference)         │ │
           │ │ • claude-3-haiku (text generation)  │ │
           │ │ • titan-embed-text-v2 (embeddings) │ │
           │ └─────────────────────────────────────┘ │
           │                                         │
           │ ┌─────────────────────────────────────┐ │
           │ │ AWS Transcribe (ASR)                │ │
           │ │ • English, Hindi support            │ │
           │ │ • Converts audio to text            │ │
           │ └─────────────────────────────────────┘ │
           │                                         │
           │ ┌─────────────────────────────────────┐ │
           │ │ AWS Polly (TTS)                     │ │
           │ │ • English, Hindi voices             │ │
           │ │ • Converts text to audio            │ │
           │ └─────────────────────────────────────┘ │
           │                                         │
           └─────────────────────────────────────────┘
                     │              │
                     ▼              ▼
           ┌─────────────────────────────────────┐
           │   EXTERNAL SERVICES                 │
           │                                     │
           │ ┌──────────────────────────────────┐│
           │ │ Pinecone Vector DB               ││
           │ │ • Farmer knowledge embeddings    ││
           │ │ • Similarity search              ││
           │ │ • RAG document retrieval         ││
           │ └──────────────────────────────────┘│
           │                                     │
           │ ┌──────────────────────────────────┐│
           │ │ OpenAI (Odia support)            ││
           │ │ • Whisper (Odia ASR)             ││
           │ │ • TTS (Odia speech synthesis)    ││
           │ └──────────────────────────────────┘│
           │                                     │
           └─────────────────────────────────────┘
                     │              │
                     ▼              ▼
           ┌─────────────────────────────────────┐
           │      AWS DATA SERVICES              │
           │                                     │
           │ ┌──────────────────────────────────┐│
           │ │ S3 Bucket                        ││
           │ │ farmer-voice-audio-*             ││
           │ │ • Audio uploads (1hr expiry)     ││
           │ │ • TTS responses (1day expiry)    ││
           │ │ • Temporary files (1hr expiry)   ││
           │ │ • CORS enabled                   ││
           │ └──────────────────────────────────┘│
           │                                     │
           │ ┌──────────────────────────────────┐│
           │ │ DynamoDB Table                   ││
           │ │ farmer-voice-rate-limits-*       ││
           │ │ • Rate limit tracking            ││
           │ │ • Session management             ││
           │ │ • TTL auto-expiry                ││
           │ └──────────────────────────────────┘│
           │                                     │
           │ ┌──────────────────────────────────┐│
           │ │ CloudWatch                       ││
           │ │ • Lambda logs                    ││
           │ │ • Error tracking                 ││
           │ │ • Performance metrics            ││
           │ └──────────────────────────────────┘│
           │                                     │
           └─────────────────────────────────────┘
```

## API Flow Diagrams

### 1. Text Q&A Flow (RAG)
```
User Browser
     │
     └─ POST /ask {"question": "..."}
            │
            ▼
     FarmerRAGLambda
            │
            ├─ retrieve_documents(question)
            │        │
            │        ├─ Create embedding (Bedrock Titan)
            │        │
            │        └─ Search Pinecone vector DB
            │
            ├─ build_prompt(question, docs)
            │
            ├─ call_llm(prompt)
            │        │
            │        └─ Invoke Bedrock Claude 3 Haiku
            │
            └─ return {"question": "...", "answer": "..."}
                     │
                     ▼
                User Browser
```

### 2. Voice Upload Flow
```
User Browser
     │
     └─ POST /voice/upload-url {"filename": "...", "content_type": "..."}
            │
            ▼
     VoiceUploadUrlLambda
            │
            └─ Generate pre-signed S3 PUT URL
                     │
                     ▼
     Return {"upload_url": "...", "s3_key": "...", "expires_in": 3600}
                     │
                     ▼
     User Browser
            │
            └─ PUT {audio file} to upload_url
                     │
                     ▼
     AWS S3 (farmer-voice-audio-*)
```

### 3. Speech-to-Text (ASR) Flow
```
User Browser
     │
     └─ POST /voice/asr {"s3_key": "audio/..."}
     │        Headers: X-Language: en, X-Session-Id: ...
     │
     ▼
VoiceASRLambda
     │
     ├─ Check rate limit (DynamoDB)
     │
     ├─ Fetch audio from S3
     │
     ├─ Route to ASR engine based on language:
     │  ├─ English/Hindi → AWS Transcribe
     │  └─ Odia → OpenAI Whisper
     │
     ├─ Invoke ASR service
     │
     └─ return {"transcription": "...", "confidence": 0.95}
              │
              ▼
       User Browser
```

### 4. Text-to-Speech (TTS) Flow
```
User Browser
     │
     └─ POST /voice/tts {"text": "...", "voice_id": "..."}
     │        Headers: X-Language: en
     │
     ▼
VoiceTTSLambda
     │
     ├─ Check rate limit (DynamoDB)
     │
     ├─ Route to TTS engine based on language:
     │  ├─ English/Hindi → AWS Polly
     │  └─ Odia → OpenAI TTS
     │
     ├─ Invoke TTS service
     │
     ├─ Save audio to S3
     │
     └─ return {"audio_url": "s3-presigned-url", "duration": 12.5}
              │
              ▼
       User Browser
```

### 5. Full Voice Pipeline Flow
```
User Browser
     │
     └─ POST /voice/ask {"s3_key": "audio/...", "output_language": "en"}
            │
            ▼
     VoicePipelineLambda
            │
            ├─ Stage 1: ASR (Speech-to-Text)
            │   └─ Convert audio to transcription
            │
            ├─ Stage 2: RAG (Question-Answering)
            │   └─ Use transcription as question
            │       └─ Retrieve documents from Pinecone
            │       └─ Generate answer with LLM
            │
            ├─ Stage 3: TTS (Text-to-Speech)
            │   └─ Convert answer to audio
            │       └─ Save to S3
            │
            └─ return {"transcription": "...", "answer": "...", "audio_url": "..."}
                     │
                     ▼
                User Browser
```

## Swagger UI Integration

```
Browser
  │
  └─ GET / (root URL)
       │
       ▼
  SwaggerUILambda
       │
       └─ Serves HTML with:
           ├─ Swagger UI JavaScript
           ├─ CSS styling
           └─ Pointer to /openapi.json
                │
                ▼
            Browser loads /openapi.json
                │
                ▼
            OpenAPISpecLambda
                │
                └─ Returns OpenAPI 3.0 JSON
                     │
                     ▼
            Swagger UI renders:
            ├─ All endpoints
            ├─ Request/response schemas
            ├─ "Try it out" buttons
            ├─ Example requests
            └─ Live response display
```

## Data Flow - Request to Response

```
Client Request
     │
     ├─ Headers: Content-Type, Authorization, X-Language, X-Session-Id
     ├─ Body: JSON with query/question/audio key
     │
     ▼
API Gateway (Custom Domain or CloudFront)
     │
     ├─ CORS validation
     ├─ Authentication (if configured)
     │
     ▼
Lambda Function
     │
     ├─ Parse event (body, headers, query params)
     ├─ Validate input
     ├─ Call business logic
     │
     ├─ External calls:
     │  ├─ Pinecone API (embeddings search)
     │  ├─ Bedrock API (LLM inference)
     │  ├─ AWS Transcribe (ASR)
     │  ├─ AWS Polly (TTS)
     │  ├─ OpenAI API (Whisper, TTS)
     │  ├─ S3 (audio upload/download)
     │  └─ DynamoDB (rate limiting)
     │
     ├─ Format response
     │
     ▼
API Gateway
     │
     ├─ Add CORS headers
     ├─ Serialize to JSON
     │
     ▼
Client Response
     ├─ Status Code (200, 400, 429, etc.)
     ├─ Headers: Content-Type, CORS headers
     └─ Body: JSON response
```

## Security Architecture

```
┌─────────────────────────────────────────────┐
│         AWS API Gateway                     │
│  • Rate limiting (built-in)                 │
│  • WAF integration (optional)                │
│  • CORS validation                          │
│  • Request validation                       │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│         Lambda Execution                    │
│  • IAM roles per function                   │
│  • Least privilege access                   │
│  • Secrets Manager integration              │
│  • Encrypted environment variables          │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│         Data Security                       │
│  • S3: Encryption at rest + transit         │
│  • DynamoDB: Point-in-time recovery         │
│  • Pinecone: API key stored securely        │
│  • OpenAI: API key in Secrets Manager       │
│  • Audio files auto-expire in S3            │
└─────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│    AWS SAM Template (template-voice.yaml) │
│                                          │
│  Resources:                              │
│  ├─ Lambdas (7 functions)               │
│  ├─ API Gateway (with Swagger)          │
│  ├─ S3 Bucket (audio storage)           │
│  ├─ DynamoDB Table (rate limits)        │
│  └─ IAM Roles & Policies                │
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│    CloudFormation Stack                 │
│    farmer-rag-voice-stack               │
│                                          │
│    Creates & manages all resources      │
│    in one atomic operation              │
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│    AWS Resources Created                │
│                                          │
│    Production-ready API with:           │
│    ✓ Auto-scaling                       │
│    ✓ High availability                  │
│    ✓ Monitoring (CloudWatch)            │
│    ✓ Logging                            │
│    ✓ Error handling                     │
│    ✓ Rate limiting                      │
│    ✓ Data persistence                   │
└─────────────────────────────────────────┘
```

## Performance & Scaling

- **Lambda Concurrency**: Auto-scaling (default: 1000 concurrent executions)
- **API Gateway Throttling**: 10,000 requests/second (default)
- **S3 Throughput**: 5,500 PUT/1,000 GET operations per second per partition
- **DynamoDB**: On-demand billing (scales automatically)
- **Pinecone**: Dedicated index with vector DB scaling
- **Bedrock**: Multi-model endpoint with provisioned throughput (optional)

## Cost Optimization

| Component | Optimization | Savings |
|-----------|--------------|---------|
| Lambda | Use correct memory size | 20-40% |
| S3 | Set lifecycle policies | 30-50% |
| DynamoDB | On-demand pricing | Auto-scales |
| Bedrock | Provisioned throughput | 30-50% (high volume) |
| Data Transfer | CloudFront caching | 40-60% |

---

**This architecture provides:**
- ✅ Scalability (auto-scaling Lambda, DynamoDB)
- ✅ Reliability (multi-AZ, managed services)
- ✅ Security (IAM, encryption, rate limiting)
- ✅ Observability (CloudWatch, logs)
- ✅ Cost efficiency (pay-per-use model)
