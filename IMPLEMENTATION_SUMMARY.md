# Farmer RAG Backend - Swagger Implementation Summary

## ✅ What Was Added

Your backend now has a complete **Swagger UI** setup for testing and documenting all API endpoints. Here's what was implemented:

### Files Created
1. **`src/swagger_handler.py`** (438 lines)
   - `swagger_ui_handler()` - Serves the interactive Swagger UI interface
   - `openapi_spec_handler()` - Serves the OpenAPI 3.0 specification
   - Complete API documentation with all endpoints, request/response schemas, and examples

2. **`SWAGGER_SETUP.md`** - Comprehensive setup and usage guide
3. **`test_with_swagger.sh`** - Quick reference for testing all endpoints
4. **`postman_collection.json`** - Pre-configured Postman collection

### Files Updated
1. **`template-voice.yaml`** - Added 2 new Lambda functions to API Gateway:
   - `SwaggerUILambda` - Serves Swagger UI HTML
   - `OpenAPISpecLambda` - Serves OpenAPI specification
   - New routes: `/` and `/openapi.json`

2. **`src/requirements.txt`** - Added:
   - `flask` - Web framework
   - `flask-cors` - CORS support for frontend integration

## 🚀 Quick Start

### 1. Deploy Your Backend

```bash
cd /Volumes/SatyBkup/projects/FARMER-POC/farmer-poc-rag-lambda

# Build the SAM application
sam build

# Deploy (this will prompt for configuration)
sam deploy --guided
```

### 2. Access Swagger UI After Deployment

Once deployed, SAM will output:
```
SwaggerUIEndpoint: https://{api-id}.execute-api.ap-south-1.amazonaws.com/Prod/
```

**Open this URL in your browser** to see the interactive Swagger UI!

### 3. Test Your Endpoints

In Swagger UI, you can:
- ✅ View all available endpoints
- ✅ See detailed documentation for each endpoint
- ✅ Test endpoints directly from the browser
- ✅ View request/response schemas

## 📡 Available Endpoints

All endpoints are documented in Swagger UI:

### Text Q&A (RAG)
```
GET /ask?query=...          - Ask a question with query parameter
POST /ask                   - Ask a question with JSON body
```

### Voice - Upload
```
POST /voice/upload-url      - Get pre-signed S3 URL for audio upload
```

### Voice - Speech-to-Text
```
POST /voice/asr             - Convert audio to text (ASR)
```

### Voice - Text-to-Speech
```
POST /voice/tts             - Convert text to audio (TTS)
```

### Health
```
GET /health                 - Health check endpoint
```

## 🧪 Example Testing in Swagger UI

### Test RAG (Text Q&A)
1. Open Swagger UI in browser
2. Expand "RAG - Text Q&A" section
3. Click "POST /ask"
4. Click "Try it out"
5. Enter request body:
   ```json
   {
     "question": "What is the best time to plant rice?"
   }
   ```
6. Click "Execute"
7. See the response below

### Test Voice Features
1. Same process for Voice endpoints
2. Swagger UI shows all required headers and parameters
3. View response examples in real-time

## 📦 Alternative: Use Postman

Already created `postman_collection.json` with all endpoints pre-configured:

1. Open Postman
2. Click "Import" → "Link"
3. Paste: `https://{api-id}.execute-api.ap-south-1.amazonaws.com/Prod/openapi.json`
4. Postman automatically creates a collection with all endpoints

Or import the `postman_collection.json` file directly from the repo.

## 🔧 Key Features

### Interactive Documentation
- Real-time API documentation
- Automatic schema validation
- Live request/response examples

### No Code Testing
- Test all endpoints from the browser
- No curl commands or Postman needed
- Perfect for demos and prototyping

### Frontend Integration Ready
- OpenAPI spec can be used by your Next.js frontend
- CORS headers configured
- All endpoints documented and discoverable

### Multi-Language Support
- Headers for language selection (en, hi, od)
- ASR/TTS language examples included
- Session tracking with X-Session-Id

## 📝 Customization

To customize Swagger UI documentation:

1. Edit `src/swagger_handler.py`
2. Modify the OpenAPI specification in `openapi_spec_handler()`
3. Update endpoint descriptions, examples, schemas
4. Redeploy with `sam deploy`

## 🔗 Integration with Frontend

Your Next.js frontend (`farmer-voice-web`) can:
1. Use the `/openapi.json` endpoint to discover APIs
2. Call the voice endpoints with proper headers
3. Test before integrating with actual frontend code

Example from your Next.js app:
```typescript
// src/lib/api.ts
const API_URL = 'https://{api-id}.execute-api.ap-south-1.amazonaws.com/Prod';

export async function askQuestion(question: string) {
  const response = await fetch(`${API_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  });
  return response.json();
}
```

## 📊 Deployment Output to Expect

After `sam deploy`, you'll see output like:
```
CloudFormation outputs from deployed stack
Outputs
│ Key              │ Value                                              │
├──────────────────┼────────────────────────────────────────────────────┤
│ SwaggerUIEndpoi… │ https://xyz123.execute-api.ap-south-1.amazonaws… │
│ OpenAPISpecEndp… │ https://xyz123.execute-api.ap-south-1.amazonaws… │
│ RAGApiEndpoint   │ https://xyz123.execute-api.ap-south-1.amazonaws… │
```

**The first URL is your Swagger UI endpoint** - open it in your browser!

## ✨ Benefits

| Feature | Before | After |
|---------|--------|-------|
| Test endpoints | Manual curl commands | Interactive Swagger UI |
| API Documentation | Readme only | Auto-generated docs |
| Schema validation | Manual | Automatic |
| Testing tool | Postman/curl | Browser-based |
| Discovery | Manual reading | Built-in explorer |
| Onboarding | Complex setup | Open URL and test |

## 🐛 Troubleshooting

### "404 Not Found" on Swagger UI URL
- Check your SAM deployment completed successfully
- Verify you're using the correct URL from deployment output
- Make sure you used `sam deploy --guided` (not just `sam deploy`)

### Swagger UI shows but endpoints fail
- Check CloudWatch logs for Lambda errors
- Verify environment variables are set (PINECONE_API_KEY, etc.)
- Ensure IAM roles have correct permissions

### CORS errors when testing
- The implementation includes CORS headers
- If issues persist, check API Gateway CORS settings
- Verify the Lambda functions are responding with proper headers

## 📚 Documentation Files

- **SWAGGER_SETUP.md** - Complete setup and detailed usage guide
- **test_with_swagger.sh** - curl command examples for all endpoints
- **postman_collection.json** - Postman collection ready to import

## 🎯 Next Steps

1. ✅ **Deploy**: Run `sam build && sam deploy --guided`
2. ✅ **Test**: Open Swagger UI and test endpoints
3. ✅ **Integrate**: Connect your Next.js frontend to the API
4. ✅ **Monitor**: Set up CloudWatch alarms for Lambda functions
5. ✅ **Optimize**: Adjust memory/timeout based on actual usage

## 📞 Support Resources

- Swagger UI built-in documentation
- OpenAPI 3.0 specification
- AWS SAM documentation
- CloudWatch logs for debugging
- Test scripts included in repo

---

**Your backend is now ready for interactive testing and documentation!** 🚀

Open the Swagger UI URL from your SAM deployment output and start testing immediately.
