# Farmer RAG Lambda (AWS Bedrock + Pinecone)

This repository is a **boilerplate** for a small end‑to‑end GenAI POC:

- Dataset of farmers / soil / weather / crop recommendations
- Embeddings generated using **AWS Bedrock** (Titan Embeddings)
- Semantic search over vectors stored in **Pinecone**
- RAG (Retrieval‑Augmented Generation) to answer questions
- Served as a **serverless API** using **AWS Lambda + API Gateway** via **AWS SAM**

---

## 🗂 Project Structure

```text
farmer-rag-lambda/
├── lambda/
│   ├── handler.py                # Lambda entrypoint
│   ├── config.py                 # Environment/config access
│   ├── embeddings/
│   │   ├── embed.py              # Bedrock embedding helper
│   │   └── pinecone_client.py    # Pinecone init + upsert + query
│   ├── ingestion/
│   │   ├── load_dataset.py       # CSV loader (local usage)
│   │   └── process_csv.py        # Convert rows → text docs
│   ├── rag/
│   │   ├── retrieve.py           # RAG retrieval using embeddings
│   │   └── prompt.py             # Prompt builder for LLM
│   ├── llm/
│   │   └── bedrock_client.py     # Bedrock LLM caller
│   ├── utils/
│   │   └── logger.py             # Basic logging
│   └── requirements.txt          # Lambda dependencies
├── data/
│   └── farmer_dataset.csv        # Placeholder dataset (replace with real one)
└── template.yaml                 # AWS SAM template for Lambda + API Gateway
```

---

## ✅ Prerequisites

- Python **3.10+**
- AWS account with:
  - **Bedrock** access enabled in your region (e.g. `ap-south-1` where available / or update)
  - Permissions for:
    - `bedrock:InvokeModel`
    - `bedrock:InvokeModelWithResponseStream`
    - S3 read (if you later use S3)
- A **Pinecone** account + API key
- **AWS SAM CLI** installed (`sam --version`)
- AWS credentials configured locally (`aws configure`)

---

## 🧾 Environment Variables (used by Lambda)

These are defined in `template.yaml` as Lambda environment variables:

- `AWS_REGION` – e.g. `ap-south-1`
- `EMBED_MODEL` – e.g. `amazon.titan-embed-text-v2`
- `LLM_MODEL` – e.g. `anthropic.claude-3-haiku-20240307-v1:0`
- `PINECONE_API_KEY` – your Pinecone API key
- `PINECONE_INDEX` – name of your Pinecone index (e.g. `farmer-rag-index`)

---

## 🧑‍💻 Local Setup (Repo Level)

1. **Create a project folder and unzip**

   ```bash
   mkdir farmer-rag-lambda
   cd farmer-rag-lambda
   # copy / unzip the provided ZIP contents here
   ```

2. **(Optional) Create a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install Lambda dependencies (for local testing)**

   ```bash
   cd lambda
   pip install -r requirements.txt
   cd ..
   ```

4. **Replace the placeholder dataset**

   - Open `data/farmer_dataset.csv`
   - Replace the dummy content with your real 100‑record dataset.

---

## 🧱 Pinecone Setup

1. Sign in to [Pinecone](https://www.pinecone.io/) and create a project.
2. Create an **index**:
   - Name: `farmer-rag-index` (or match `PINECONE_INDEX`)
   - Metric: `cosine`
   - Dimension: must match the Titan embedding dimension (e.g., 1536 or as per model).
3. Copy your **Pinecone API key** and keep it handy for:
   - Local `.env` (if you create one)
   - Lambda environment variable `PINECONE_API_KEY`.

> Note: This boilerplate assumes the embeddings dimension matches your index dimension. Adjust as needed based on the actual model specs.

---

## 🔁 (Optional) One‑time Ingestion Script

Right now this boilerplate focuses on **query‑time RAG**.

For a proper pipeline you typically want:

- A **local or Lambda script** that:
  - Loads `data/farmer_dataset.csv`
  - Converts each row → text using `process_csv.row_to_text`
  - Calls `embed_text(text)` to get vector
  - Writes vectors to Pinecone via `store_embedding`

This ingestion step can be implemented as a separate script:

```python
# example skeleton (not included as a Lambda handler yet)

from ingestion.load_dataset import load_local_dataset
from ingestion.process_csv import prepare_documents
from embeddings.embed import embed_text
from embeddings.pinecone_client import store_embedding

def run_ingestion():
    df = load_local_dataset("data/farmer_dataset.csv")
    docs = prepare_documents(df)
    for doc in docs:
        vec = embed_text(doc["text"])
        store_embedding(doc["id"], vec, doc["metadata"])

if __name__ == "__main__":
    run_ingestion()
```

You can run this **once** from your local machine (with valid AWS + Bedrock + Pinecone credentials) to populate the index.

---

## ☁️ Deploying to AWS with SAM

1. **Validate SAM template**

   ```bash
   sam validate
   ```

2. **Build the Lambda package**

   ```bash
   sam build
   ```

3. **Deploy (guided)**

   ```bash
   sam deploy --guided
   ```

   During the guided deploy, SAM will ask you for:
   - Stack name (e.g. `farmer-rag-stack`)
   - AWS region
   - Whether to save the configuration for future deploys
   - You can then override environment variables in the console/parameters if desired.

4. After deploy, SAM will output an **API Gateway URL**, something like:

   ```text
   https://xxxxxx.execute-api.ap-south-1.amazonaws.com/Prod/ask
   ```

   You can query it with:

   ```bash
   curl "https://xxxxxx.execute-api.ap-south-1.amazonaws.com/Prod/ask?query=best+crop+for+loamy+soil+in+Odisha"
   ```

---

## 🔍 How the Runtime Flow Works

1. User hits: `GET /ask?query=...`
2. API Gateway triggers **Lambda** (`handler.lambda_handler`).
3. Lambda:
   - Reads `query` from `event["queryStringParameters"]["query"]`
   - Calls `retrieve_documents(query)`:
     - Embeds query with Bedrock (Titan)
     - Queries Pinecone for top‑K similar records
   - Builds a RAG prompt from returned contexts.
   - Calls `call_llm(prompt)` using Bedrock (Claude, Llama, etc.)
   - Returns LLM answer as HTTP response.

---

## ✅ TODO – Step‑by‑Step Checklist

Use this as your practical TODO list:

1. [ ] Create AWS account & configure `aws configure` locally  
2. [ ] Enable **Bedrock** in your selected region  
3. [ ] Create **Pinecone** account and index (`farmer-rag-index`)  
4. [ ] Unzip this boilerplate into a local folder / GitHub repo  
5. [ ] Replace `data/farmer_dataset.csv` with your 100‑record dataset  
6. [ ] Implement and run a one‑time **ingestion script** to:
    - [ ] Load CSV  
    - [ ] Convert rows → text  
    - [ ] Generate embeddings via Bedrock  
    - [ ] Upsert vectors into Pinecone  
7. [ ] Update `template.yaml` environment variables:
    - [ ] `AWS_REGION`  
    - [ ] `EMBED_MODEL`  
    - [ ] `LLM_MODEL`  
    - [ ] `PINECONE_API_KEY`  
    - [ ] `PINECONE_INDEX`  
8. [ ] Run `sam build`  
9. [ ] Run `sam deploy --guided`  
10. [ ] Test your endpoint via `curl` / Postman / browser  
11. [ ] (Optional) Add API key / Cognito to secure the endpoint  
12. [ ] (Optional) Add CloudWatch dashboards for latency & errors  
13. [ ] (Optional) Add a simple web/mobile UI on top of the `/ask` endpoint  

---

## 🧪 Testing Locally (Basic)

You can do basic unit tests locally by simulating the Lambda event:

```python
from lambda.handler import lambda_handler

event = {
    "queryStringParameters": {
        "query": "best crop for loamy soil in Odisha"
    }
}
response = lambda_handler(event, None)
print(response)
```

You can also explore `sam local invoke` or `sam local start-api` for more advanced local testing.

---

## 📝 Notes

- This boilerplate is intentionally minimal so you can shape it as you like.
- You may want to:
  - Replace `eval(...)` parsing with proper JSON parsing for safety.
  - Add error handling and timeouts around Bedrock/Pinecone calls.
  - Introduce retry logic and circuit breakers for production use.
  - Add logging and correlation IDs for observability.

---

Happy building! 🚜🌾  
If you extend this with weather APIs, multi‑agent logic, or a UI, this backend will still be a solid core to plug into.
