# AI Use Disclosure

This document outlines how AI technologies were used in the development of the **NVIDIA RAG Research Assistant**.

---

## 🔍 Overview

The NVIDIA Research Assistant integrates multiple AI components to enable comprehensive analysis of NVIDIA's quarterly reports, valuation data, and real-time insights. The system employs Retrieval-Augmented Generation (RAG), document parsing, embeddings, and Large Language Models (LLMs).

---

## 🤖 AI Tools and Libraries Used

### 1. **Large Language Models (LLMs)**

- **OpenAI GPT-4 / GPT-3.5-turbo**  
  Used via LangChain to answer user queries and generate summary reports using context retrieved from documents and databases.

- **Claude 3 Sonnet**  
  Assisted in designing prompts, planning architecture, and generating high-quality summaries and citations.

### 2. **Embeddings and Vector Search**

- **HuggingFace Transformers**  
  The `all-MiniLM-L6-v2` model was used to convert document chunks into vector embeddings.

- **Pinecone**  
  Served as the vector database for semantic search and metadata-based filtering by year, quarter, and source.

### 3. **Document Parsing**

- **Mistral OCR (Jina)**  
  Used to parse complex financial PDF files and extract structured content.

- **Docling (experimental)**  
  Used for structured extraction of PDF layouts when OCR was not sufficient.

---

## 🎯 Purposes of AI Usage

| Area | AI Contribution |
|------|-----------------|
| **Document Understanding** | Extracted structured content from PDF reports using OCR and AI parsing. |
| **Semantic Search (RAG)** | Enabled users to find relevant answers across 20+ quarterly reports using vector similarity and LLMs. |
| **Query Answering** | LLMs generated natural-language answers using retrieved context, with citations to quarter and page. |
| **Financial Summary** | AI was used to summarize valuation trends (e.g., P/E, EV/EBITDA) pulled from Snowflake. |
| **Web Search Integration** | Real-time headlines and news were included in reports using a Google Search API + LLM summarization. |
| **Code Generation** | AI was used during development to scaffold Python code, SQL queries, and debug integration issues. |

---

## 🛠️ Human Review and Control

While AI supported development, **all code, prompts, data handling, and outputs were manually reviewed** and improved by human developers. Special attention was given to:

- Grounding LLM responses in retrieved content
- Preventing hallucinations or fabricated metrics
- Ensuring SQL and Snowflake data were validated

---

## ⚠️ Limitations and Considerations

- AI-generated answers depend on the quality of parsed documents and embedding accuracy.
- LLMs may hallucinate if context is missing; safeguards are implemented via prompt instructions and fallback messages.
- Time filtering is done via metadata (`year`, `quarter`, `quarter_label`) and is subject to parsing accuracy.
- The system is optimized for NVIDIA reports and would require tuning for other companies.

---

## 📦 Development Tools with AI Integration

- **LangChain**
- **SentenceTransformers**
- **Pinecone SDK**
- **OpenAI SDK**
- **Claude Sonnet (via Poe)**
- **Streamlit** (used AI-enhanced UI iterations)
- **FastAPI** (manual backend with AI-assisted debugging)

---

## ✅ Responsible AI Practices

- All AI use was transparent and documented.
- No private data or user queries are stored.
- Open-source models were used for embedding to ensure reproducibility.
- API keys and credentials are stored securely via environment variables.

---

_Last updated: {{ today’s date }}_
