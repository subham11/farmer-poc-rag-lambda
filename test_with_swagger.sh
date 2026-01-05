#!/bin/bash
# Quick test examples for Farmer RAG API with Swagger UI
# 
# Usage: Update API_URL with your actual API Gateway endpoint from deployment output
# Then run individual commands to test endpoints

# ============================================================================
# CONFIGURATION
# ============================================================================
API_URL="https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/Prod"
SESSION_ID="farmer-session-$(date +%s)"

echo "=========================================="
echo "Farmer RAG Voice API - Quick Test Guide"
echo "=========================================="
echo ""
echo "API URL: $API_URL"
echo "Session ID: $SESSION_ID"
echo ""
echo "Update API_URL in this script with your actual endpoint from SAM deployment"
echo ""

# ============================================================================
# 1. TEST SWAGGER UI
# ============================================================================
echo ""
echo "1. ACCESS SWAGGER UI (Browser)"
echo "=========================================="
echo "Swagger UI:     $API_URL/"
echo "OpenAPI Spec:   $API_URL/openapi.json"
echo ""
echo "Open these URLs in your browser to test endpoints interactively"
echo ""

# ============================================================================
# 2. TEST HEALTH CHECK
# ============================================================================
echo ""
echo "2. TEST HEALTH CHECK"
echo "=========================================="
echo "Command:"
echo "curl -X GET $API_URL/health -H 'Content-Type: application/json'"
echo ""
echo "Or with full example:"
echo ""
health_test() {
    echo "curl -X GET \"$API_URL/health\" \\"
    echo "  -H 'Content-Type: application/json'"
}
health_test

echo ""

# ============================================================================
# 3. TEST RAG QUERY (GET)
# ============================================================================
echo ""
echo "3. TEST RAG QUERY - GET Method"
echo "=========================================="
rag_get_test() {
    echo "curl -X GET \"$API_URL/ask?query=What%20is%20the%20best%20time%20to%20plant%20rice\" \\"
    echo "  -H 'Content-Type: application/json'"
}
rag_get_test

echo ""

# ============================================================================
# 4. TEST RAG QUERY (POST)
# ============================================================================
echo ""
echo "4. TEST RAG QUERY - POST Method"
echo "=========================================="
rag_post_test() {
    echo "curl -X POST \"$API_URL/ask\" \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"question\": \"How do I prevent crop diseases?\"}'"
}
rag_post_test

echo ""

# ============================================================================
# 5. TEST VOICE UPLOAD URL
# ============================================================================
echo ""
echo "5. TEST VOICE UPLOAD URL"
echo "=========================================="
voice_upload_test() {
    echo "curl -X POST \"$API_URL/voice/upload-url\" \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -H 'X-Language: en' \\"
    echo "  -d '{\"filename\": \"farmer_query.wav\", \"content_type\": \"audio/wav\"}'"
}
voice_upload_test

echo ""

# ============================================================================
# 6. TEST SPEECH-TO-TEXT (ASR)
# ============================================================================
echo ""
echo "6. TEST SPEECH-TO-TEXT (ASR)"
echo "=========================================="
asr_test() {
    echo "curl -X POST \"$API_URL/voice/asr\" \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -H 'X-Language: en' \\"
    echo "  -H 'X-Session-Id: $SESSION_ID' \\"
    echo "  -d '{\"s3_key\": \"audio/farmer_query_20240102_120000.wav\"}'"
}
asr_test

echo ""

# ============================================================================
# 7. TEST TEXT-TO-SPEECH (TTS)
# ============================================================================
echo ""
echo "7. TEST TEXT-TO-SPEECH (TTS)"
echo "=========================================="
tts_test() {
    echo "curl -X POST \"$API_URL/voice/tts\" \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -H 'X-Language: en' \\"
    echo "  -d '{\"text\": \"The best time to plant rice is during the monsoon season.\"}'"
}
tts_test

echo ""

# ============================================================================
# 8. FULL WORKFLOW EXAMPLE
# ============================================================================
echo ""
echo "=========================================="
echo "COMPLETE WORKFLOW EXAMPLE"
echo "=========================================="
echo ""
echo "Step 1: Ask a question (RAG)"
echo "-------"
echo "curl -X POST \"$API_URL/ask\" \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"question\": \"How to improve soil fertility?\"}' | jq '.answer'"
echo ""
echo "Expected: Detailed answer from RAG pipeline"
echo ""
echo "Step 2: Convert answer to speech (TTS)"
echo "-------"
echo "ANSWER=\"\$(curl -s -X POST \"$API_URL/ask\" \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"question\": \"How to improve soil fertility?\"}' | jq -r '.answer')\""
echo ""
echo "curl -X POST \"$API_URL/voice/tts\" \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'X-Language: en' \\"
echo "  -d \"{\\\"text\\\": \\\"$ANSWER\\\"}\" | jq '.audio_url'"
echo ""
echo "Expected: S3 pre-signed URL for audio download"
echo ""

# ============================================================================
# 9. USING THE SWAGGER UI DIRECTLY
# ============================================================================
echo ""
echo "=========================================="
echo "USING SWAGGER UI (RECOMMENDED)"
echo "=========================================="
echo ""
echo "1. Open browser: $API_URL/"
echo ""
echo "2. Click 'RAG - Text Q&A' section to expand"
echo ""
echo "3. Click 'POST /ask' endpoint"
echo ""
echo "4. Click 'Try it out' button"
echo ""
echo "5. Enter test question in the request body:"
echo "   {\"question\": \"What is the best fertilizer for wheat?\"}"
echo ""
echo "6. Click 'Execute'"
echo ""
echo "7. View response in 'Response' section"
echo ""

# ============================================================================
# 10. IMPORTING INTO POSTMAN
# ============================================================================
echo ""
echo "=========================================="
echo "IMPORTING INTO POSTMAN"
echo "=========================================="
echo ""
echo "1. Open Postman"
echo "2. Click 'Import' button (top left)"
echo "3. Go to 'Link' tab"
echo "4. Paste: $API_URL/openapi.json"
echo "5. Click 'Continue' and then 'Import'"
echo ""
echo "Postman will automatically create a collection with all endpoints"
echo ""

# ============================================================================
# 11. ENVIRONMENT VARIABLES FOR TESTING
# ============================================================================
echo ""
echo "=========================================="
echo "SAVE THESE FOR QUICK TESTING"
echo "=========================================="
echo ""
cat > farmer_api_env.sh << 'EOF'
#!/bin/bash
# Save this as farmer_api_env.sh and source it: source farmer_api_env.sh

export API_URL="https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/Prod"
export SESSION_ID="farmer-$(date +%s)"

# Quick test functions
ask_question() {
    local q="$1"
    curl -s -X POST "$API_URL/ask" \
      -H 'Content-Type: application/json' \
      -d "{\"question\": \"$q\"}" | jq '.'
}

get_upload_url() {
    local filename="${1:-query.wav}"
    curl -s -X POST "$API_URL/voice/upload-url" \
      -H 'Content-Type: application/json' \
      -H 'X-Language: en' \
      -d "{\"filename\": \"$filename\", \"content_type\": \"audio/wav\"}" | jq '.'
}

convert_to_speech() {
    local text="$1"
    curl -s -X POST "$API_URL/voice/tts" \
      -H 'Content-Type: application/json' \
      -H 'X-Language: en' \
      -d "{\"text\": \"$text\"}" | jq '.'
}

echo "✓ Environment loaded!"
echo "Use: ask_question \"Your question here\""
echo "Use: get_upload_url \"filename.wav\""
echo "Use: convert_to_speech \"Text to convert\""
EOF

echo "Created: farmer_api_env.sh"
echo "Usage: source farmer_api_env.sh"
echo ""
echo "Then use quick functions:"
echo "  ask_question \"What causes crop disease?\""
echo "  get_upload_url \"my_audio.wav\""
echo "  convert_to_speech \"This is a test message\""
echo ""

echo ""
echo "=========================================="
echo "NEXT STEPS"
echo "=========================================="
echo ""
echo "1. Deploy your backend:"
echo "   cd /Volumes/SatyBkup/projects/FARMER-POC/farmer-poc-rag-lambda"
echo "   sam build && sam deploy --guided"
echo ""
echo "2. Get your API endpoint from deployment output"
echo ""
echo "3. Update API_URL in this script or in farmer_api_env.sh"
echo ""
echo "4. Open Swagger UI in browser: API_URL/"
echo ""
echo "5. Test endpoints interactively in Swagger UI"
echo ""
echo "6. Or use curl commands from this guide"
echo ""
