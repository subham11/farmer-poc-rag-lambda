# Swagger UI Setup for Farmer RAG Backend

This guide explains how to use the Swagger UI for testing your Farmer RAG Voice API endpoints.

## Overview

A complete Swagger/OpenAPI setup has been added to your backend, allowing you to:
- View all available API endpoints
- See detailed documentation for each endpoint
- Test endpoints directly from the browser
- View request/response schemas and examples

## What Was Added

### New Files
1. **`src/swagger_handler.py`** - Lambda functions for serving Swagger UI and OpenAPI spec
2. **Updated `src/requirements.txt`** - Added Flask and CORS dependencies

### Updated Files
1. **`template-voice.yaml`** - Added Swagger Lambda functions and API Gateway routes

## Deployment

### 1. Deploy with SAM

```bash
cd /Volumes/SatyBkup/projects/FARMER-POC/farmer-poc-rag-lambda

# Build the application
sam build

# Deploy (guided)
sam deploy --guided
```

When prompted, use these settings:
- **Function Name**: `farmer-voice-app` (or your preferred name)
- **Region**: `ap-south-1` (or your preferred region)
- **Parameter PineconeApiKey**: Enter your Pinecone API key
- **Parameter OpenAIApiKey**: Enter your OpenAI API key (optional)

### 2. After Deployment

The SAM deployment will output several URLs. Look for:
- `SwaggerUIEndpoint` - The Swagger UI interface
- `OpenAPISpecEndpoint` - The raw OpenAPI specification

## Accessing Swagger UI

After deployment:

1. **Access Swagger UI**: Navigate to the `SwaggerUIEndpoint` URL in your browser
   ```
   https://{api-id}.execute-api.ap-south-1.amazonaws.com/Prod/
   ```

2. The Swagger UI will automatically load and display all available endpoints

## Available Endpoints

### RAG - Text Q&A
- **GET /ask** - Ask a question with query parameter
  ```
  ?query=What is the best time to plant rice?
  ```
- **POST /ask** - Ask a question with JSON body
  ```json
  {
    "question": "How do I prevent crop diseases?"
  }
  ```

### Voice - Audio Management
- **POST /voice/upload-url** - Get pre-signed S3 URL for audio upload
- **POST /voice/asr** - Convert audio to text (Speech-to-Text)
- **POST /voice/tts** - Convert text to audio (Text-to-Speech)
- **POST /voice/ask** - Full voice pipeline (ASR → RAG → TTS)

### Health
- **GET /health** - Health check endpoint

## Testing in Swagger UI

### 1. Test Text Q&A

1. Find the **"RAG - Text Q&A"** section
2. Click **"POST /ask"**
3. Click **"Try it out"**
4. Enter a JSON body:
   ```json
   {
     "question": "What is the best time to plant rice?"
   }
   ```
5. Click **"Execute"**
6. View the response below

### 2. Test Voice Upload

1. Find **"Voice - Audio Upload"** section
2. Click **"POST /voice/upload-url"**
3. Click **"Try it out"**
4. Enter request body:
   ```json
   {
     "filename": "farmer_query.wav",
     "content_type": "audio/wav"
   }
   ```
5. Add header: `X-Language: en`
6. Click **"Execute"**
7. Use the returned `upload_url` to upload your audio file via PUT request

### 3. Test Speech-to-Text (ASR)

1. Find **"Voice - Speech-to-Text (ASR)"** section
2. Click **"POST /voice/asr"**
3. Click **"Try it out"**
4. Enter request body with S3 key from upload:
   ```json
   {
     "s3_key": "audio/farmer_query_20240102_120000.wav"
   }
   ```
5. Add headers:
   - `X-Language: en`
   - `X-Session-Id: session-123`
6. Click **"Execute"**

### 4. Test Text-to-Speech (TTS)

1. Find **"Voice - Text-to-Speech (TTS)"** section
2. Click **"POST /voice/tts"**
3. Click **"Try it out"**
4. Enter request body:
   ```json
   {
     "text": "The best time to plant rice is during the monsoon season."
   }
   ```
5. Add header: `X-Language: en`
6. Click **"Execute"**
7. Download the audio from the returned `audio_url`

## Request/Response Examples

### RAG Query Example
```bash
curl -X POST https://{api-id}.execute-api.ap-south-1.amazonaws.com/Prod/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How to improve soil fertility?"
  }'
```

**Response:**
```json
{
  "question": "How to improve soil fertility?",
  "answer": "Soil fertility can be improved by... [detailed answer from RAG pipeline]"
}
```

### Voice Upload Example
```bash
curl -X POST https://{api-id}.execute-api.ap-south-1.amazonaws.com/Prod/voice/upload-url \
  -H "Content-Type: application/json" \
  -H "X-Language: en" \
  -d '{
    "filename": "query.wav",
    "content_type": "audio/wav"
  }'
```

**Response:**
```json
{
  "upload_url": "https://s3.ap-south-1.amazonaws.com/...",
  "s3_key": "audio/query_20240102_120000.wav",
  "expires_in": 3600
}
```

## Swagger UI Features

### Collapse/Expand Sections
Click on tag names to collapse/expand endpoint groups

### Model Schemas
Scroll down to see data model schemas for request/response bodies

### Authentication
If your endpoints require auth headers (like API keys), you can:
1. Click the **"Authorize"** button (if configured)
2. Enter credentials
3. Subsequent requests will include the auth header

### Export OpenAPI Spec
The OpenAPI spec can be imported into:
- **Postman** - For advanced testing
- **API Gateway** - For additional AWS integrations
- **Third-party API tools** - For documentation generation

## Customization

### Modify API Documentation

To update endpoint descriptions, parameters, or examples, edit `src/swagger_handler.py`:

```python
"summary": "Your new summary",
"description": "Your new description",
"example": "New example value"
```

### Add More Endpoints

1. Add endpoint details to the `"paths"` section in `openapi_spec_handler()`
2. Redeploy with SAM

### Customize Swagger UI Theme

Edit the HTML in `swagger_ui_handler()` to change:
- Layout (layout: "BaseLayout" or "StandaloneLayout")
- Preset plugins
- Custom CSS styling

## Troubleshooting

### Swagger UI shows "404 Not Found"
- Ensure the deployment completed successfully
- Check the `SwaggerUIEndpoint` URL from deployment output
- Verify API Gateway is properly configured

### OpenAPI spec returns empty
- Check that `openapi_spec_handler()` function is properly deployed
- Verify the `/openapi.json` route is configured in `template-voice.yaml`

### CORS errors when testing from Swagger UI
- The OpenAPI spec includes CORS headers in responses
- If still experiencing issues, update API Gateway CORS settings

### Cannot upload audio files
- Verify S3 bucket exists and has correct CORS configuration
- Check IAM permissions for the Lambda function
- Ensure pre-signed URL hasn't expired

## Local Testing

### Use SAM Local

```bash
# Start local API Gateway
sam local start-api

# Access Swagger UI locally
curl http://localhost:3000/
```

### Use Python Test Scripts

The repo includes test scripts:
```bash
python test_voice_api.py      # Test voice endpoints
python test_api.py            # Test RAG endpoints
python test_voice_local.py    # Test locally
```

## Next Steps

1. ✅ Deploy your backend with Swagger UI
2. Test each endpoint using Swagger UI
3. Integrate with your frontend (farmer-voice-web)
4. Monitor API usage in CloudWatch
5. Set up API monitoring and alerts

## Support

For issues or questions:
- Check CloudWatch logs for Lambda functions
- Review API Gateway error responses
- Verify environment variables are set correctly
- Test with curl before testing with Swagger UI
