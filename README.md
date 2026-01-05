# Farmer RAG Lambda - Complete Voice & Text AI Backend

[![AWS SAM](https://img.shields.io/badge/AWS%20SAM-1.0-orange)](https://aws.amazon.com/serverless/sam/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![Swagger](https://img.shields.io/badge/Swagger-UI-brightgreen)](https://swagger.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A complete **serverless AI backend** for farmer assistance with **voice and text capabilities**, featuring Retrieval-Augmented Generation (RAG), speech-to-text, text-to-speech, and interactive API documentation.

## 🌟 Key Features

- **🤖 AI-Powered Q&A**: RAG system using AWS Bedrock (Claude 3) + Pinecone vector search
- **🎤 Voice Processing**: Full voice pipeline with ASR (speech-to-text) and TTS (text-to-speech)
- **🌐 Multi-Language**: English, Hindi, and Odia language support
- **📚 Interactive Documentation**: Complete Swagger UI for API testing and exploration
- **🔧 One-Click Deployment**: Automated AWS deployment with comprehensive testing
- **🧪 Production Ready**: CORS configured, error handling, health checks, rate limiting
- **📱 Frontend Ready**: CORS-enabled for seamless frontend integration

## 🚀 Quick Start (5 minutes)

### Prerequisites
```bash
# Verify AWS setup
aws sts get-caller-identity
sam --version

# Navigate to backend
cd /Volumes/SatyBkup/projects/FARMER-POC/farmer-poc-rag-lambda
```

### Deploy to AWS
```bash
./deploy.sh
# When prompted: Enter Pinecone API key, confirm deployment
```

### Test Everything
```bash
# Extract API URL
API_URL=$(cat api_endpoint.txt | grep "API Endpoint:" | cut -d' ' -f3)

# Run comprehensive tests (should pass all 28 tests)
./test_endpoints.sh "$API_URL"
```

### Access Swagger UI
```bash
# Open in browser
cat api_endpoint.txt | grep "Swagger"
# Example: https://abc123.execute-api.ap-south-1.amazonaws.com/Prod/
```

## 📋 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [API Endpoints](#-api-endpoints)
- [Deployment Guide](#-deployment-guide)
- [Testing](#-testing)
- [Local Development](#-local-development)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │────│   API Gateway   │────│   AWS Lambda    │
│   (React/Next)  │    │   (CORS)        │    │   Functions     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌────────────────────────────────┼────────────────────────────────┐
                       │                                │                                │
            ┌──────────▼──────────┐          ┌──────────▼──────────┐          ┌──────────▼──────────┐
            │   AWS Bedrock      │          │     Pinecone        │          │     AWS S3         │
            │   (LLM + Embed)    │          │   (Vector DB)       │          │   (Audio Storage)  │
            └───────────────────┘          └─────────────────────┘          └─────────────────────┘
                       │                                │                                │
            ┌──────────▼──────────┐          ┌──────────▼──────────┐          ┌──────────▼──────────┐
            │   AWS Transcribe   │          │   AWS Polly         │          │     OpenAI         │
            │   (Speech-to-Text) │          │   (Text-to-Speech)   │          │   (Odia Support)   │
            └───────────────────┘          └─────────────────────┘          └─────────────────────┘
```

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Gateway** | AWS | REST API routing with CORS |
| **Lambda Functions** | Python 3.11 | Serverless compute (7 functions) |
| **Bedrock** | AWS | Claude 3 LLM + Titan embeddings |
| **Pinecone** | Vector DB | Semantic search over farmer data |
| **S3** | AWS | Audio file storage with lifecycle |
| **DynamoDB** | AWS | Rate limiting with TTL |
| **Transcribe/Polly** | AWS | Voice processing (EN/HI) |
| **OpenAI** | External | Odia language support |

### Data Flow

1. **Text Q&A**: Query → Embed → Search Pinecone → RAG Prompt → Claude → Response
2. **Voice Input**: Audio → Transcribe → Text Query → RAG → Polly → Audio Response
3. **Voice Output**: Text Response → Polly/OpenAI → Audio URL

---

## 📡 API Endpoints

### Base URL
```
https://{api-id}.execute-api.ap-south-1.amazonaws.com/Prod
```

### Core Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/` | **Swagger UI** - Interactive API documentation | ✅ |
| `GET` | `/openapi.json` | OpenAPI 3.0 specification | ✅ |
| `GET` | `/health` | API health status | ✅ |
| `GET` | `/ask?query=...` | Text Q&A with query parameter | ✅ |
| `POST` | `/ask` | Text Q&A with JSON body | ✅ |
| `POST` | `/voice/upload-url` | Get S3 upload URL for audio | ✅ |
| `POST` | `/voice/asr` | Speech-to-Text conversion | ✅ |
| `POST` | `/voice/tts` | Text-to-Speech conversion | ✅ |
| `POST` | `/voice/ask` | Full voice pipeline (ASR → RAG → TTS) | ✅ |

### Request/Response Examples

#### Text Q&A
```bash
# GET request
curl "https://api.example.com/ask?query=What is the best fertilizer for rice?"

# POST request
curl -X POST "https://api.example.com/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I prevent crop diseases?"}'

# Response
{
  "question": "How do I prevent crop diseases?",
  "answer": "To prevent crop diseases effectively: 1. Crop rotation... 2. Seed selection...",
  "sources": ["farmer_dataset.csv (Section: Disease Management)"],
  "language": "en",
  "processing_time": 1.89
}
```

#### Voice Processing
```bash
# Get upload URL
curl -X POST "https://api.example.com/voice/upload-url" \
  -H "Content-Type: application/json" \
  -d '{"filename": "question.wav", "content_type": "audio/wav"}'

# Speech-to-Text
curl -X POST "https://api.example.com/voice/asr" \
  -H "Content-Type: application/json" \
  -H "X-Language: en" \
  -d '{"s3_key": "audio/question.wav"}'

# Text-to-Speech
curl -X POST "https://api.example.com/voice/tts" \
  -H "Content-Type: application/json" \
  -H "X-Language: hi" \
  -d '{"text": "नमस्ते, मैं आपकी मदद कर सकता हूं"}'
```

### Language Support

| Language | Code | ASR | TTS | Notes |
|----------|------|-----|-----|-------|
| English | `en` | AWS Transcribe | AWS Polly | Primary language |
| Hindi | `hi` | AWS Transcribe | AWS Polly | Indian language support |
| Odia | `od` | OpenAI Whisper | OpenAI TTS | Regional language |

### Error Responses

```json
// 400 Bad Request
{
  "error": "Bad Request",
  "message": "Missing required parameter: question",
  "details": "Please provide either 'question' in POST body or 'query' as URL parameter"
}

// 429 Too Many Requests
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded",
  "details": "Maximum 10 requests per minute per session",
  "retry_after": 45
}

// 500 Internal Server Error
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred",
  "request_id": "abc-123-def-456"
}
```

---

## 🚀 Deployment Guide

### Prerequisites

- **AWS Account** with Bedrock access enabled
- **AWS CLI** configured (`aws configure`)
- **AWS SAM CLI** installed (`sam --version`)
- **Pinecone Account** with API key
- **Python 3.11+** for local testing

### One-Command Deployment

```bash
cd /Volumes/SatyBkup/projects/FARMER-POC/farmer-poc-rag-lambda

# Deploy everything automatically
./deploy.sh
```

**During deployment, provide:**
- Stack Name: `farmer-rag-lambda`
- Region: `ap-south-1`
- PineconeApiKey: Your Pinecone API key
- OpenAIApiKey: (Optional) For Odia support

### Manual Deployment

```bash
# Validate template
sam validate --template template-voice.yaml

# Build application
sam build --use-container

# Deploy with guidance
sam deploy --guided
```

### Post-Deployment

```bash
# Get all endpoints
cat api_endpoint.txt

# Test health
curl "$API_URL/health"

# Run comprehensive tests
./test_endpoints.sh "$API_URL"
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `ap-south-1` |
| `PINECONE_API_KEY` | Pinecone API key | `your-key-here` |
| `PINECONE_INDEX` | Pinecone index name | `farmer-rag-index` |
| `OPENAI_API_KEY` | OpenAI API key (optional) | `sk-...` |

---

## 🧪 Testing

### Automated Test Suite

Run the comprehensive 28-test suite:

```bash
# Get API URL
API_URL=$(cat api_endpoint.txt | grep "API Endpoint:" | cut -d' ' -f3)

# Run all tests
./test_endpoints.sh "$API_URL"
```

**Test Coverage:**
- ✅ Swagger UI & OpenAPI spec
- ✅ CORS configuration
- ✅ Text Q&A endpoints (GET/POST)
- ✅ Voice processing endpoints
- ✅ Health checks
- ✅ Multi-language support
- ✅ Error handling
- ✅ Rate limiting

### Manual Testing

#### Swagger UI Testing
1. Open Swagger URL in browser
2. Expand any endpoint
3. Click "Try it out"
4. Enter test data
5. Click "Execute"

#### Postman Testing
```bash
# Import OpenAPI spec
# File → Import → Link
# Paste: https://your-api-url/openapi.json
```

#### Local Testing
```bash
# Start local server (no Docker needed)
python -c "
from src.swagger_handler import swagger_ui_handler, openapi_spec_handler
import json

# Test Swagger UI
result = swagger_ui_handler({}, {})
print('Swagger UI Status:', result['statusCode'])

# Test OpenAPI spec
result = openapi_spec_handler({}, {})
spec = json.loads(result['body'])
print('OpenAPI Version:', spec['openapi'])
print('Endpoints:', len(spec['paths']))
"
```

---

## 💻 Local Development

### Project Structure

```
farmer-poc-rag-lambda/
├── src/
│   ├── handler.py              # Main Lambda handler
│   ├── swagger_handler.py      # Swagger UI + OpenAPI spec
│   ├── config.py               # Configuration management
│   ├── requirements.txt        # Python dependencies
│   ├── embeddings/
│   │   ├── embed.py            # AWS Bedrock embeddings
│   │   └── pinecone_client.py  # Pinecone vector operations
│   ├── ingestion/
│   │   ├── load_dataset.py     # CSV data loading
│   │   └── process_csv.py      # Data preprocessing
│   ├── llm/
│   │   └── bedrock_client.py   # AWS Bedrock LLM calls
│   ├── rag/
│   │   ├── retrieve.py         # Vector search & retrieval
│   │   └── prompt.py           # RAG prompt construction
│   ├── utils/
│   │   └── logger.py           # Logging utilities
│   └── voice/
│       ├── handlers.py         # Voice endpoint handlers
│       ├── config.py           # Voice configuration
│       ├── rate_limiter.py     # Rate limiting
│       ├── s3_manager.py       # S3 operations
│       ├── asr/
│       │   ├── router.py       # ASR routing logic
│       │   ├── transcribe_client.py # AWS Transcribe
│       │   └── whisper_client.py    # OpenAI Whisper
│       └── tts/
│           ├── router.py       # TTS routing logic
│           ├── openai_client.py     # OpenAI TTS
│           └── polly_client.py      # AWS Polly
├── data/
│   └── farmer_dataset.csv      # Training dataset
├── docs/
│   └── VOICE_AI_ARCHITECTURE.md # Voice architecture
├── template-voice.yaml         # CloudFormation template
├── deploy.sh                   # Deployment script
├── test_endpoints.sh           # Test suite
└── README.md                   # This file
```

### Setup Development Environment

```bash
# Clone or navigate to project
cd /Volumes/SatyBkup/projects/FARMER-POC/farmer-poc-rag-lambda

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r src/requirements.txt

# Setup Pinecone (one-time)
python setup_pinecone.py
```

### Local Testing

```bash
# Test individual functions
python test_api.py

# Test voice endpoints locally
python test_voice_local.py

# Test with Swagger UI locally
python -c "
from http.server import HTTPServer, BaseHTTPRequestHandler
from src.swagger_handler import swagger_ui_handler

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            result = swagger_ui_handler({}, {})
            self.send_response(result['statusCode'])
            self.end_headers()
            self.wfile.write(result['body'].encode())
        else:
            self.send_response(404)
            self.end_headers()

print('Starting local server on http://localhost:3000')
HTTPServer(('localhost', 3000), TestHandler).serve_forever()
"
```

### Data Ingestion

```bash
# Process and upload dataset to Pinecone
python -c "
from src.ingestion.load_dataset import load_local_dataset
from src.ingestion.process_csv import prepare_documents
from src.embeddings.embed import embed_text
from src.embeddings.pinecone_client import store_embedding

# Load and process data
df = load_local_dataset('data/farmer_dataset.csv')
docs = prepare_documents(df)

# Upload to Pinecone
for doc in docs:
    vec = embed_text(doc['text'])
    store_embedding(doc['id'], vec, doc['metadata'])
    print(f'Uploaded: {doc[\"id\"]}')
"
```

---

## ⚙️ Configuration

### AWS Services Configuration

#### Bedrock Models
```yaml
# In template-voice.yaml
LLM_MODEL: anthropic.claude-3-haiku-20240307-v1:0
EMBED_MODEL: amazon.titan-embed-text-v2
```

#### Pinecone Setup
```python
# Index configuration
INDEX_NAME = "farmer-rag-index"
DIMENSION = 1536  # Titan embedding dimension
METRIC = "cosine"
```

#### S3 Configuration
```yaml
# Audio storage bucket
VoiceAudioBucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketName: farmer-audio-bucket
    CorsConfiguration:
      CorsRules:
        - AllowedOrigins: ['*']
          AllowedMethods: [GET, PUT, POST]
          AllowedHeaders: ['*']
```

### Rate Limiting

```python
# DynamoDB table for rate limiting
RateLimitTable:
  Type: AWS::DynamoDB::Table
  Properties:
    TableName: farmer-rate-limits
    AttributeDefinitions:
      - AttributeName: session_id
        AttributeType: S
    KeySchema:
      - AttributeName: session_id
        KeyType: HASH
    BillingMode: PAY_PER_REQUEST
```

### CORS Configuration

```yaml
# API Gateway CORS
Globals:
  Api:
    Cors:
      AllowMethods: "'GET,POST,OPTIONS,PUT,DELETE'"
      AllowHeaders: "'Content-Type,X-Session-Id,X-Language,Authorization'"
      AllowOrigin: "'*'"
      MaxAge: "'86400'"
```

---

## 🔧 Troubleshooting

### Common Issues

#### Deployment Fails
```bash
# Check AWS credentials
aws sts get-caller-identity

# Validate CloudFormation template
sam validate --template template-voice.yaml

# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name farmer-rag-lambda
```

#### API Returns Errors
```bash
# Check Lambda logs
aws logs tail /aws/lambda/farmer-rag-lambda-AskLambda --follow

# Test health endpoint
curl "$API_URL/health"

# Check CORS headers
curl -i -X OPTIONS "$API_URL/" \
  -H "Access-Control-Request-Method: POST"
```

#### Voice Endpoints Fail
```bash
# Check S3 permissions
aws s3 ls s3://farmer-audio-bucket/

# Verify Pinecone connection
python -c "from src.embeddings.pinecone_client import test_connection; test_connection()"

# Check OpenAI key (if using Odia)
echo $OPENAI_API_KEY
```

#### Rate Limiting Issues
```bash
# Check DynamoDB table
aws dynamodb scan --table-name farmer-rate-limits

# Clear rate limits (development only)
aws dynamodb delete-table --table-name farmer-rate-limits
```

### Performance Optimization

#### Lambda Memory/Timeout
```yaml
# In template-voice.yaml
AskLambda:
  Properties:
    MemorySize: 2048  # Increase for better performance
    Timeout: 30       # Increase for complex queries
```

#### CloudWatch Monitoring
```bash
# View Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=farmer-rag-lambda-AskLambda \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Logs and Debugging

```bash
# View all Lambda log groups
aws logs describe-log-groups --query 'logGroups[*].logGroupName' | grep farmer

# Tail specific function logs
aws logs tail /aws/lambda/farmer-rag-lambda-AskLambda --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name "/aws/lambda/farmer-rag-lambda-AskLambda" \
  --filter-pattern "ERROR"
```

---

## 📚 Documentation Files

| File | Description |
|------|-------------|
| `AWS_DEPLOYMENT_GUIDE.md` | Complete deployment instructions |
| `QUICK_REFERENCE.md` | Fast command reference |
| `TEST_RESULTS_REFERENCE.md` | Expected test outputs |
| `SWAGGER_IMPLEMENTATION_SUMMARY.md` | Technical implementation details |
| `DEPLOYMENT_CHECKLIST.md` | Pre/post deployment checklist |
| `ARCHITECTURE.md` | System architecture diagrams |
| `IMPLEMENTATION_SUMMARY.md` | What was implemented |
| `SETUP_COMPLETE.md` | Setup verification |

---

## 🤝 Contributing

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Make** your changes
4. **Test** locally: `./test_endpoints.sh`
5. **Commit** changes: `git commit -am 'Add new feature'`
6. **Push** to branch: `git push origin feature/your-feature`
7. **Create** Pull Request

### Code Standards

- **Python**: PEP 8 style, type hints recommended
- **AWS SAM**: Follow serverless best practices
- **Documentation**: Keep README and docs updated
- **Testing**: Add tests for new features

### Adding New Endpoints

1. Add handler function in appropriate module
2. Update `template-voice.yaml` with new Lambda function
3. Add API Gateway route
4. Update OpenAPI spec in `swagger_handler.py`
5. Add tests to `test_endpoints.sh`
6. Update documentation

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **AWS** for Bedrock, Lambda, API Gateway, and other services
- **Pinecone** for vector database capabilities
- **OpenAI** for Odia language support
- **Swagger** for API documentation tools

---

## 📞 Support

For issues or questions:

1. **Check the docs**: See troubleshooting section above
2. **Review logs**: Use CloudWatch or local testing
3. **Test locally**: Use the provided test scripts
4. **Check GitHub Issues**: Search existing issues
5. **Create Issue**: For new problems with reproduction steps

---

**Happy farming with AI! 🚜🌾**

*Built with ❤️ using AWS Serverless technologies*
