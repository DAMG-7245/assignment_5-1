author: Group1
summary: Building a Multi-Agent NVIDIA Valuation Assistant using LangGraph, Snowflake, and Streamlit
id: NVIDIA-Financial-Research-Assistant
categories: AI, Agent, LangGraph, Snowflake, LLM
environments: Web
status: Published


# Multi-Agent NVIDIA Valuation Assistant

## Overview

|                 |                                                                 |
|-----------------|-----------------------------------------------------------------|
| **Target**      | Intermediate Python developers, data engineers, ML/NLP builders |
| **Duration**    | ~60–90 minutes                                                  |
| **You'll build**| A multi-agent RAG system for NVIDIA's financial insights        |


A multi-agent research assistant that answers user questions about NVIDIA by combining structured financial data from **Snowflake**, unstructured quarterly reports via **RAG + Pinecone**, and real-time news using **web search agents**. The system is orchestrated using **LangGraph** and served through a **Streamlit** interface.

### Prerequisites
- Python 3.12
- AWS Account (for S3)

## 🚀 Features

- 🤖 **Multi-Agent Architecture (LangGraph)**:
  - `Snowflake Agent`: Queries NVIDIA financial valuation metrics.
  - `RAG Agent`: Retrieves insights from quarterly reports via Pinecone (hybrid search with metadata filtering).
  - `Web Search Agent`: Fetches recent news and market sentiment using web search APIs (e.g., SerpAPI, Tavily).

- 📊 **Structured Data Support**:
  - Pulls valuation metrics (e.g., P/E, Market Cap) from Yahoo Finance.
  - Populates Snowflake table: `RAW.NVIDIA_VALUATION_METRICS`.

- 📄 **Unstructured Data Processing**:
  - Parses NVIDIA quarterly PDF reports.
  - Embeds text chunks with metadata (`year`, `quarter`) into Pinecone for RAG.

- 🧠 **LLM-Powered Reasoning**:
  - Answers analytical questions using LangChain + OpenAI or Mistral.
  - Each agent returns LLM-generated responses with charts or citations.

- 🖥️ **Streamlit Frontend**:
  - Simple UI for querying by quarter, year, and selecting agents.
  - Displays generated answers and charts.


## Step 1: Project Setup

### Clone Repository & Install Dependencies
```bash
git clone https://github.com/DAMG-7245/assignment_5-1.git

```

### 📦 Create virtual environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

### Configure Environment Variables
Create `.env` file:
```ini
# Snowflake
SNOWFLAKE_ACCOUNT=your_account_id
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=LANG_DB
SNOWFLAKE_SCHEMA=RAW
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_ROLE=your_role

# S3
S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# OpenAI
OPENAI_API_KEY=sk-...

# Pinecone
PINECONE_API_KEY=your_key
PINECONE_ENVIRONMENT=gcp-starter

# Jina (optional)
JINA_AUTH_TOKEN=sk-xxx

```
## Step 2: Load Valuation Metrics into Snowflake

```bash
python data/ingest_yahoo_excel.py
```

This script will:
- Download structured Excel file from S3
- Parse and clean it
- Insert valuation metrics into `RAW.NVIDIA_VALUATION_METRICS`

---
## Step 3: Scrape Real-Time Metrics via Yahoo Finance

```bash
python data/nvidia_yfin.py
```

This script hits `yfinance` to fetch the latest forward PE, PEG, etc., and formats it into a consistent quarterly structure.

---


## Step 4: Parse NVIDIA PDFs and Embed into Pinecone

```bash
curl -X POST http://localhost:8000/api/index-reports
```

This triggers:

1. Reading an Excel from S3 (`quarter_label`, `url`).
2. Downloading and parsing each PDF using Jina (or OCR fallback).
3. Splitting the text into semantic chunks.
4. Embedding via SentenceTransformers.
5. Uploading to Pinecone with metadata:
   - `quarter_label`, `year`, `quarter`, `source`, `text`, `page`


---

## Step 5: Multi-Agent Query Interface

### 🔁 How Multi-Agent Integration Works

The `/api/agent-query` endpoint accepts:

```json
{
  "query": "Summarize NVIDIA's growth and valuation in 2024",
  "agents": ["rag", "snowflake", "web_search"],
  "time_range": {
    "start_quarter": "2024q1",
    "end_quarter": "2024q4"
  }
}
```

Each agent is responsible for:

- `rag_agent`: Searches semantic PDF chunks from Pinecone based on the time range.
- `snowflake_agent`: Queries valuation metrics like PE, EV/EBITDA, Market Cap by quarter.
- `web_search_agent`: Pulls relevant news headlines and summaries via SerpAPI or Google.

The **orchestrator** (in `core/orchestrator.py`) coordinates all enabled agents and merges their results into a unified `AgentResponse`.

---

## Step 6: Generate Comprehensive Reports (RAG + Metrics + News)

```json
POST /api/generate-report
{
  "time_range": {
    "start_quarter": "2024q1",
    "end_quarter": "2024q4"
  }
}
```

The orchestrator will:

1. Fetch metrics from Snowflake.
2. Search Pinecone for semantic content.
3. Pull news insights.
4. Use an LLM (e.g., Claude or Google Gemini) to synthesize a detailed report with:
   - 📈 Historical financials
   - 🔍 Strategic observations
   - 🌐 Market sentiment


## Step 7: Start the Backend API

```bash
cd backend
uvicorn main:app --reload
```

- Exposes endpoints for RAG query orchestration
- Connects to Pinecone and Snowflake
- Logs metadata, matches, and outputs

---

## Step 8: Run the Streamlit Frontend
```bash
cd frontend
streamlit run app.py
```

- Choose time range (e.g., Q1–Q4 2024)
- Click “Generate Comprehensive Report”
- Results are based on:
  - Valuation metrics from Snowflake
  - Semantic context from Pinecone
  - News from SerpAPI (optional)


## Final Deliverables Checklist
- [x] Structured ingestion of valuation metrics
- [x] S3 → Snowflake pipeline via pandas
- [x] Retrieval-augmented generation with LangChain + Pinecone
- [x] API + Streamlit frontend
- [x] `.md` documentation: AIUseDisclosure, architecture, and this Codelab


## API 
### Agent-query
```python
@app.post("/api/agent-query")
```
### Generate-report
```python
@app.post("/api/generate-report")
```
### Index-reports
```python
@app.post("/api/index-reports")
```
### Indexing-status
```python
@app.get("/api/indexing-status")
```
### Available-quarters
```python
@app.get("/api/available-quarters")
```

## Test locally
### Backend
```bash
cd backend
uvicorn main:app
```
### Frontend(Replace localhost url)
```bash
cd frontend
streamlit run main.py
```


## Deployment
### Dockerfile
```bash
docker build --platform=linux/amd64 -t gcr.io/YOUR_PROJECT_ID/fastapi-app .
docker run --rm -it --env-file .env --platform linux/amd64 gcr.io/YOUR_PROJECT_ID/fastapi-app
docker push gcr.io/YOUR_PROJECT_ID/fastapi-app
gcloud run deploy fastapi-service \
  --image gcr.io/YOUR_PROJECT_ID/fastapi-app \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated
```

