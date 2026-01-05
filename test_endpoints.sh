#!/bin/bash

# Farmer RAG Backend - Comprehensive Test Suite
# Tests all endpoints with various scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${1:-http://localhost:3000}"
SESSION_ID="test-session-$(date +%s)"
TESTS_PASSED=0
TESTS_FAILED=0

# Remove trailing slash
API_URL="${API_URL%/}"

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║        FARMER RAG BACKEND - COMPREHENSIVE TEST SUITE                       ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Test Configuration:"
echo "   API URL: $API_URL"
echo "   Session ID: $SESSION_ID"
echo ""

# Helper function for test results
test_result() {
    local test_name=$1
    local http_status=$2
    local expected_status=$3
    local response=$4
    
    if [ "$http_status" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name (Status: $http_status)"
        echo "   Response: $(echo $response | head -c 100)..."
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo "   Expected: $expected_status, Got: $http_status"
        echo "   Response: $response"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# ============================================================================
# TEST 1: SWAGGER UI & DOCUMENTATION
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST GROUP 1: SWAGGER UI & DOCUMENTATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 1.1: Swagger UI loads
echo "Test 1.1: Swagger UI HTML..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "Swagger UI HTML loads" "$HTTP_CODE" "200" "$BODY"

# Test 1.2: OpenAPI Spec
echo "Test 1.2: OpenAPI Specification..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/openapi.json")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "OpenAPI specification available" "$HTTP_CODE" "200" "$BODY"

# Verify OpenAPI has correct structure
if echo "$BODY" | grep -q "openapi.*3.0.0"; then
    echo -e "${GREEN}✅ PASS${NC}: OpenAPI version 3.0.0 detected"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: OpenAPI version not found"
    ((TESTS_FAILED++))
fi
echo ""

# ============================================================================
# TEST 2: CORS CONFIGURATION
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST GROUP 2: CORS CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 2.1: OPTIONS preflight
echo "Test 2.1: OPTIONS preflight request..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X OPTIONS "$API_URL/" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "OPTIONS preflight accepted" "$HTTP_CODE" "200" "$BODY"

# Test 2.2: CORS headers present
echo "Test 2.2: CORS headers in response..."
HEADERS=$(curl -s -i -X OPTIONS "$API_URL/" \
  -H "Access-Control-Request-Method: POST" 2>&1)
if echo "$HEADERS" | grep -q "Access-Control-Allow-Origin"; then
    echo -e "${GREEN}✅ PASS${NC}: CORS headers present"
    echo "$HEADERS" | grep "Access-Control" | sed 's/^/   /'
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: CORS headers not found"
    ((TESTS_FAILED++))
fi
echo ""

# ============================================================================
# TEST 3: TEXT Q&A (RAG) ENDPOINTS
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST GROUP 3: TEXT Q&A (RAG) ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 3.1: GET /ask with query parameter
echo "Test 3.1: GET /ask with query parameter..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/ask?query=What%20is%20the%20best%20fertilizer%20for%20rice")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "GET /ask with query parameter" "$HTTP_CODE" "200" "$BODY"

# Test 3.2: POST /ask with JSON body
echo "Test 3.2: POST /ask with JSON body..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I prevent crop diseases?"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "POST /ask with JSON body" "$HTTP_CODE" "200" "$BODY"

# Verify response has question and answer fields
if echo "$BODY" | grep -q '"question"'; then
    echo -e "${GREEN}✅ PASS${NC}: Response contains 'question' field"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠️  WARNING${NC}: Response doesn't contain 'question' field"
fi

if echo "$BODY" | grep -q '"answer"'; then
    echo -e "${GREEN}✅ PASS${NC}: Response contains 'answer' field"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠️  WARNING${NC}: Response doesn't contain 'answer' field"
fi
echo ""

# Test 3.3: Missing query parameter
echo "Test 3.3: Error handling - missing query parameter..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/ask")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "Missing query parameter error" "$HTTP_CODE" "400" "$BODY"

# ============================================================================
# TEST 4: VOICE ENDPOINTS
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST GROUP 4: VOICE ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 4.1: POST /voice/upload-url
echo "Test 4.1: POST /voice/upload-url..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/voice/upload-url" \
  -H "Content-Type: application/json" \
  -H "X-Language: en" \
  -d '{"filename": "test_audio.wav", "content_type": "audio/wav"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "POST /voice/upload-url" "$HTTP_CODE" "200" "$BODY"

# Test 4.2: POST /voice/asr (Speech-to-Text)
echo "Test 4.2: POST /voice/asr (Speech-to-Text)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/voice/asr" \
  -H "Content-Type: application/json" \
  -H "X-Language: en" \
  -H "X-Session-Id: $SESSION_ID" \
  -d '{"s3_key": "audio/test_audio.wav"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "POST /voice/asr" "$HTTP_CODE" "200" "$BODY"

# Test 4.3: POST /voice/tts (Text-to-Speech)
echo "Test 4.3: POST /voice/tts (Text-to-Speech)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/voice/tts" \
  -H "Content-Type: application/json" \
  -H "X-Language: en" \
  -d '{"text": "The best time to plant rice is during the monsoon season."}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "POST /voice/tts" "$HTTP_CODE" "200" "$BODY"

# ============================================================================
# TEST 5: HEALTH CHECK
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST GROUP 5: HEALTH CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 5.1: GET /health
echo "Test 5.1: GET /health endpoint..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/health")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "GET /health" "$HTTP_CODE" "200" "$BODY"

# ============================================================================
# TEST 6: LANGUAGE SUPPORT
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST GROUP 6: LANGUAGE SUPPORT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 6.1: Hindi language
echo "Test 6.1: POST /voice/tts with Hindi..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/voice/tts" \
  -H "Content-Type: application/json" \
  -H "X-Language: hi" \
  -d '{"text": "नमस्ते"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "Hindi language support" "$HTTP_CODE" "200" "$BODY"

# Test 6.2: Odia language
echo "Test 6.2: POST /voice/tts with Odia..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/voice/tts" \
  -H "Content-Type: application/json" \
  -H "X-Language: od" \
  -d '{"text": "ନମସ୍କାର"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "Odia language support" "$HTTP_CODE" "200" "$BODY"

# ============================================================================
# TEST 7: ERROR HANDLING
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST GROUP 7: ERROR HANDLING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Test 7.1: Invalid endpoint
echo "Test 7.1: Invalid endpoint (404)..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/invalid-endpoint")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "Invalid endpoint returns 404" "$HTTP_CODE" "404" "$BODY"

# Test 7.2: Invalid JSON
echo "Test 7.2: Invalid JSON body..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/ask" \
  -H "Content-Type: application/json" \
  -d 'invalid json')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
test_result "Invalid JSON handling" "$HTTP_CODE" "400" "$BODY"

# ============================================================================
# TEST SUMMARY
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! ($TOTAL_TESTS/$TOTAL_TESTS)${NC}"
    exit 0
else
    SUCCESS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))
    echo -e "${YELLOW}⚠️  SOME TESTS FAILED${NC}: $SUCCESS_RATE% pass rate ($TESTS_PASSED/$TOTAL_TESTS)"
    exit 1
fi
