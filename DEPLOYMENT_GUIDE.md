# Deployment Instructions - Farmer RAG with Swagger UI

## Prerequisites

Before deploying, ensure you have:

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **SAM CLI** (AWS Serverless Application Model)
4. **Python 3.11+**
5. **Pinecone API Key** (for RAG embeddings)
6. **OpenAI API Key** (optional, for Odia language support)

### Install SAM CLI

```bash
# macOS
brew tap aws/tap
brew install aws-sam-cli

# Or visit: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html
```

### Verify Installation

```bash
sam --version
aws --version
python3 --version
```

## Deployment Steps

### Step 1: Prepare Your Environment

```bash
cd /Volumes/SatyBkup/projects/FARMER-POC/farmer-poc-rag-lambda

# Optional: Create/activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

### Step 2: Build the Application

```bash
sam build
```

This command:
- Installs dependencies from `src/requirements.txt`
- Builds Lambda function packages
- Generates `.aws-sam/build/` directory
- Takes 2-5 minutes depending on dependencies

Output should look like:
```
Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml
```

### Step 3: Deploy with SAM (First Time)

```bash
sam deploy --guided
```

When prompted, enter:

```
Stack Name: farmer-rag-voice-stack
Region: ap-south-1
Parameter PineconeApiKey: <your-pinecone-api-key>
Parameter OpenAIApiKey: <your-openai-api-key> (or press Enter to skip)
Parameter MaxRequestsPerHour: 5

Confirm changes before deploy? [y/N]: y
```

### Step 4: Wait for Deployment

The deployment process:
- Creates CloudFormation stack
- Provisions S3 bucket for audio files
- Creates DynamoDB table for rate limiting
- Creates API Gateway and Lambda functions
- Deploys Swagger UI endpoints

Takes 3-5 minutes. Output includes:

```
CloudFormation outputs from deployed stack
├────────────────────────┬─────────────────────────────────┤
│ SwaggerUIEndpoint      │ https://xyz123.execute-api...   │
│ OpenAPISpecEndpoint    │ https://xyz123.execute-api...   │
│ RAGApiEndpoint         │ https://xyz123.execute-api...   │
└────────────────────────┴─────────────────────────────────┘
```

### Step 5: Save Configuration

After successful deployment, save your endpoints:

```bash
# Copy the SwaggerUIEndpoint URL
export API_URL="https://xyz123.execute-api.ap-south-1.amazonaws.com/Prod"

# Save to file for future use
echo "API_URL=$API_URL" > api_config.sh
```

### Step 6: Access Swagger UI

Open the **SwaggerUIEndpoint** URL in your browser:
```
https://xyz123.execute-api.ap-south-1.amazonaws.com/Prod/
```

You should see the interactive Swagger UI with all endpoints!

## Subsequent Deployments

### For Code Updates

When you update your code and want to redeploy:

```bash
sam build
sam deploy  # No --guided needed after first deployment
```

### Full Redeploy with New Parameters

```bash
sam deploy --guided --force-upload
```

## Verification After Deployment

### 1. Test Swagger UI

```bash
# Get Swagger UI
curl https://xyz123.execute-api.ap-south-1.amazonaws.com/Prod/

# Get OpenAPI spec
curl https://xyz123.execute-api.ap-south-1.amazonaws.com/Prod/openapi.json
```

### 2. Test RAG Endpoint

```bash
curl -X POST https://xyz123.execute-api.ap-south-1.amazonaws.com/Prod/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the best time to plant rice?"}'
```

### 3. Check CloudWatch Logs

```bash
# View recent logs for all functions
aws logs tail /aws/lambda/farmer-rag-voice-stack-FarmerRAGLambda-* --follow

# Or search for errors
aws logs filter-log-events --log-group-name /aws/lambda/farmer-rag-voice-stack \
  --filter-pattern "ERROR"
```

## Common Issues & Solutions

### Issue: "Pinecone API Key required"

**Solution**: Ensure you provided the key during deployment. If missing:

```bash
sam deploy --parameter-overrides \
  PineconeApiKey=your-key-here
```

### Issue: "AccessDenied" errors

**Solution**: Check IAM permissions:
```bash
# Ensure your AWS user has IAM, Lambda, API Gateway, S3, and DynamoDB permissions
aws iam list-attached-user-policies --user-name your-username
```

### Issue: Lambda timeout errors

**Solution**: Increase timeout in template-voice.yaml:
```yaml
Timeout: 60  # Increase from 30
```

Then redeploy:
```bash
sam build && sam deploy
```

### Issue: "S3 bucket already exists"

**Solution**: AWS S3 bucket names are globally unique. SAM generates unique names using your account ID, but if still failing:

```bash
# Clean up old stack
aws cloudformation delete-stack --stack-name farmer-rag-voice-stack
aws cloudformation wait stack-delete-complete --stack-name farmer-rag-voice-stack

# Then redeploy
sam deploy --guided
```

## Environment Variables

Your Lambda functions use these environment variables (set automatically):

```bash
AWS_REGION_NAME          # AWS region (ap-south-1)
AUDIO_BUCKET             # S3 bucket for audio files
RATE_LIMIT_TABLE         # DynamoDB table name
MAX_REQUESTS_PER_HOUR    # Rate limit (default: 5)
OPENAI_API_KEY           # OpenAI API key (optional)
PINECONE_API_KEY         # Pinecone API key
PINECONE_INDEX           # Pinecone index (farmer-rag-index)
EMBED_MODEL              # Embedding model (titan-embed-text-v2)
LLM_MODEL                # LLM model (claude-3-haiku)
```

## Monitoring After Deployment

### CloudWatch Dashboard

```bash
# View function invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=farmer-rag-voice-stack-FarmerRAGLambda-xxx \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### Set Up Alarms

```bash
# Create alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name farmer-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

## Rollback

If something goes wrong:

```bash
# View previous versions
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

# Rollback to previous version
aws cloudformation cancel-update-stack \
  --stack-name farmer-rag-voice-stack

# Or delete stack entirely
aws cloudformation delete-stack \
  --stack-name farmer-rag-voice-stack
```

## Cost Estimation

Monthly costs (approximate):

| Service | Estimate | Notes |
|---------|----------|-------|
| Lambda | $1-5 | Free tier: 1M invocations/month |
| API Gateway | $0.35 | Free tier: 1M calls/month |
| S3 | $0.50-2 | Storage + data transfer |
| DynamoDB | $1-3 | On-demand pricing |
| **Total** | **~$2-15** | Very low for development |

## Next Steps After Deployment

1. ✅ **Test in Swagger UI** - Open the endpoint URL
2. ✅ **Try example queries** - Use test endpoints
3. ✅ **Check CloudWatch logs** - Monitor execution
4. ✅ **Integrate with frontend** - Connect farmer-voice-web
5. ✅ **Set up CI/CD** - Automate future deployments

## CI/CD Integration (Optional)

To automate deployments with GitHub Actions:

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: aws-actions/setup-sam@v1
      - run: sam build
      - run: sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
```

## Support & Documentation

- **AWS SAM Docs**: https://docs.aws.amazon.com/serverless-application-model/
- **API Gateway**: https://docs.aws.amazon.com/apigateway/
- **Lambda**: https://docs.aws.amazon.com/lambda/
- **Swagger/OpenAPI**: https://swagger.io/specification/

---

**Ready to deploy? Run:**
```bash
sam build && sam deploy --guided
```
