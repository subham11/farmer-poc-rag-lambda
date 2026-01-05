# Deployment Checklist - CORS & Backend Changes

## ✅ Changes Made

### Code Changes
1. **`src/swagger_handler.py`** - Enhanced CORS support
   - Added `_get_cors_headers()` function for centralized CORS configuration
   - Added `cors_handler()` to handle OPTIONS preflight requests
   - Updated both handlers to include CORS headers in all responses
   - Added request interceptor in Swagger UI for CORS-safe headers

2. **`template-voice.yaml`** - Added CORS configuration
   - Added global `Api.Cors` settings at the Globals level
   - Allows all origins (`*`)
   - Allows methods: GET, POST, OPTIONS, PUT, DELETE
   - Allows headers: Content-Type, X-Session-Id, X-Language, Authorization
   - Max-Age: 86400 (24 hours for preflight caching)
   - Added OPTIONS method handlers to both Swagger Lambda functions

3. **`src/requirements.txt`** - Already updated (no changes needed)

### CORS Configuration Details

**API-Level CORS:**
```yaml
Globals:
  Api:
    Cors:
      AllowMethods: 'GET,POST,OPTIONS,PUT,DELETE'
      AllowHeaders: 'Content-Type,X-Session-Id,X-Language,Authorization'
      AllowOrigin: '*'
      MaxAge: '86400'
```

**Handler-Level CORS:**
- Each response includes proper CORS headers
- OPTIONS requests return 200 with CORS headers
- Swagger UI includes request interceptor for compatibility

---

## 🚀 Deployment Instructions

### Step 1: Verify Changes
```bash
cd /Volumes/SatyBkup/projects/FARMER-POC/farmer-poc-rag-lambda

# Check that all files are modified correctly
git status
```

### Step 2: Build
```bash
sam build
```

Expected output:
```
Build Succeeded
Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml
```

### Step 3: Deploy
```bash
sam deploy --guided
```

Or if already configured:
```bash
sam deploy
```

### Step 4: Verify Deployment
After deployment completes, you'll see:
```
CloudFormation outputs from deployed stack
Outputs
│ Key                    │ Value                                          │
├────────────────────────┼────────────────────────────────────────────────┤
│ SwaggerUIEndpoint      │ https://xxxxx.execute-api.xxx.amazonaws.com    │
│ OpenAPISpecEndpoint    │ https://xxxxx.execute-api.xxx.amazonaws.com    │
```

---

## 🧪 CORS Testing After Deployment

### Test 1: OPTIONS Preflight Request
```bash
curl -X OPTIONS https://YOUR_API_URL/ \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

Expected response headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET,POST,OPTIONS,PUT,DELETE
Access-Control-Allow-Headers: Content-Type,X-Session-Id,X-Language,Authorization
Access-Control-Max-Age: 86400
```

### Test 2: Test Swagger UI
Open browser: `https://YOUR_API_URL/`
- Should load without CORS errors
- Should be able to test endpoints from the UI

### Test 3: Test OpenAPI Spec
```bash
curl https://YOUR_API_URL/openapi.json \
  -H "Access-Control-Allow-Origin: *" \
  -i
```

Should return 200 with CORS headers and JSON spec.

### Test 4: Frontend Integration
From your Next.js frontend, test:
```javascript
fetch('https://YOUR_API_URL/ask', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Language': 'en'
  },
  body: JSON.stringify({
    question: 'Test question'
  })
})
```

Should work without CORS blocking.

---

## 📋 Files Modified Summary

| File | Changes | Scope |
|------|---------|-------|
| `src/swagger_handler.py` | Enhanced with CORS handlers | Python code |
| `template-voice.yaml` | Added global CORS + OPTIONS routes | CloudFormation |
| `src/requirements.txt` | No changes (already had flask) | Python deps |

---

## ⚠️ Important Notes

1. **CORS Allow Origin**: Currently set to `*` (allows all origins)
   - For production, consider restricting to specific domains
   - Example: `AllowOrigin: "'https://yourdomain.com'"`

2. **OPTIONS Method**: Automatically handled by API Gateway when Cors is configured
   - Both Lambda functions now explicitly handle OPTIONS
   - No preflight errors should occur

3. **Frontend Testing**:
   - After deployment, test from `farmer-voice-web` frontend
   - Update API URL in frontend to point to new endpoints
   - Ensure proper headers are sent in frontend requests

4. **Existing Voice Functions**: 
   - They already have CORS headers from their handlers
   - Global API.Cors will also apply to them automatically
   - No code changes needed in those files

---

## 🔄 Rollback Plan

If issues occur after deployment:

```bash
# View previous stack version
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE

# Rollback to previous version
aws cloudformation cancel-update-stack --stack-name farmer-rag-voice-stack

# Or delete and redeploy if needed
aws cloudformation delete-stack --stack-name farmer-rag-voice-stack
```

---

## ✅ Pre-Deployment Checklist

Before running `sam deploy`:

- [ ] All code changes have been made
- [ ] `src/swagger_handler.py` includes CORS handlers
- [ ] `template-voice.yaml` includes global CORS configuration
- [ ] `template-voice.yaml` includes OPTIONS routes for Swagger Lambdas
- [ ] No syntax errors in YAML (`sam validate` passes)
- [ ] AWS credentials are configured
- [ ] Pinecone API key is available
- [ ] S3 bucket doesn't exist yet (SAM will create it)

---

## 📊 Expected Improvements

After deployment with CORS enhancements:

| Issue | Before | After |
|-------|--------|-------|
| CORS preflight | May fail | ✅ Handled automatically |
| Frontend requests | May be blocked | ✅ Allowed with proper headers |
| Browser testing | Possible issues | ✅ Works seamlessly |
| OPTIONS requests | Not handled | ✅ Returns 200 with CORS headers |

---

## 🎯 What's Ready

✅ **Code changes complete** - All files modified  
✅ **CORS configuration added** - Both API-level and handler-level  
✅ **OPTIONS handlers added** - For preflight requests  
✅ **Ready for deployment** - Just run `sam deploy`  

---

**Next Action:** Run `sam build && sam deploy --guided`

After deployment, test the CORS configuration to ensure all endpoints are accessible from your frontend.
