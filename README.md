# Meeting Intelligence Platform

I started this project to solve a specific problem: organizations spend countless hours on calls, but extracting actionable insights, tracking historical context, and generating reports takes too much manual effort. This platform automates that entire workflow using a multi-agent AI system.

## Features

- Upload a meeting transcript (text) or audio recording and get a full structured report back — action items, risks, KPIs, decisions, participants, and a narrative summary.
- Historical comparison: the system pulls up to 4 previous meetings with the same customer and generates a trend analysis automatically.
- Reports are rendered as HTML using Jinja2 templates and emailed to the salesperson via Brevo.
- A RAG-powered chatbot lets salespeople ask questions about their past meetings in natural language. It filters results by customer, date range, or specific dates.
- Multi-tenant isolation. Every query is scoped to the logged-in user's organisation and salesperson ID. One org can never see another org's data.
- JWT authentication with access/refresh token flow. Admins can register salespeople under their org.
- Chat session history with persistent memory — the chatbot remembers the last 3 turns of conversation.

## High-Level Architecture

The backend is an asynchronous Python server built with Django Ninja and served via Uvicorn (ASGI). The heavy AI processing (report generation, embedding creation) runs as background tasks detached from the HTTP request cycle using `asyncio.create_task`. This means the API responds instantly with a `"processing"` status while the LangGraph pipeline works in the background.

### Meeting Processing Agent

<p align="center">
  <img src="agent.png" width="1100">
</p>

### RAG & Retrieval Architecture

<p align="center">
  <img src="Chatbot Architecture.png" width="1100">
</p>

## How It Works

When a salesperson uploads a transcript or audio file, here's what happens step by step:

1. The controller creates a `Meeting` object in PostgreSQL with status `"processing"` and a placeholder title like `"Meeting 5"`.
2. It schedules a background task (`asyncio.create_task`) that invokes the LangGraph pipeline.
3. LangGraph kicks off two nodes in parallel:
   - **Structured Report Node** — extracts KPIs, action items, risks, decisions, participants, etc. into a strict Pydantic schema using `with_structured_output()`.
   - **Narrative Report Node** — writes a human-readable summary of the meeting flow.
4. Both results fan into the **Historical Report Node**, which queries the last 4 meetings with the same customer and asks the LLM to compare trends.
5. After history, the graph splits again into two parallel paths:
   - **Markdown Node** — converts the structured JSON into a markdown document (for future GIN index search).
   - **HTML Node** — renders a Jinja2 template into a styled HTML report.
6. Both paths converge at **Save to DB**, which writes everything inside a single `transaction.atomic()` block. It also updates the `Meeting.title` from the generic placeholder to the AI-generated title (e.g. "Q3 Pricing Call with Netflix").
7. After the DB save, two more parallel tasks fire:
   - **Email Node** — sends the HTML report to the salesperson via Brevo.
   - **Embedding Node** — chunks the transcript using VoyageAI's SemanticChunker, generates 1024-d vector embeddings, and bulk-inserts them into PostgreSQL with metadata for filtered retrieval.
8. The meeting status is updated to `"completed"`. If anything fails at any step, it's set to `"failed"` and the full stack trace is logged.

## LLM Routing & Fallback

I use different models for different jobs based on their strengths:

- **Report generation** uses OpenRouter's Llama 3.3 70B Instruct as the primary model. If OpenRouter fails or hits a rate limit, it falls back to Google Gemini Pro automatically using LangChain's `.with_fallbacks()`. The primary model retries 3 times before giving up.
- **Chatbot responses** use Groq's GPT-OSS-120B for speed. The chat endpoint doesn't use structured output — it just needs fast, conversational text — so the model choice is optimized for latency.
- All LLM calls use `ainvoke` (async invoke) so the Django server doesn't block while waiting for a response.

```python
# How the fallback works in practice (from llm.py)
async def get_structured(self, schema, messages):
    primary_structured = self.primary_model.with_structured_output(schema)
    fallback_structured = self.fallback_model.with_structured_output(schema)
    robust = primary_structured.with_fallbacks([fallback_structured])
    return await robust.ainvoke(messages)
```

## RAG Pipeline

The chatbot retrieval pipeline runs 4 stages:

**1. Embed the query**
The user's question is embedded into a 1024-d vector using VoyageAI (`voyage-3.5`).

**2. Hybrid search**
Two separate searches run against PostgreSQL:
- *Semantic search* — uses `pgvector`'s HNSW index with cosine distance to find the closest transcript chunks by meaning.
- *Keyword search* — uses PostgreSQL's built-in full-text search (GIN index on a `SearchVectorField`) to find exact word matches.

Both searches are filtered by `organisation_id` and `salesperson_id` at the SQL level. Optional filters for `customer_id`, `start_date`, `end_date`, and `specific_date` narrow results further.

**3. Reciprocal Rank Fusion (RRF)**
The two result lists are merged using RRF with `k=60`. A chunk that ranks highly in both semantic and keyword search gets a much higher fused score than one that only appears in one list. The top 10 chunks move forward.

**4. Cross-encoder reranking**
The 10 fused chunks are reranked using Voyage AI's `rerank-2` cross-encoder model. This evaluates each chunk directly against the original query (not just embedding similarity) and returns the 5 most relevant chunks.

These 5 chunks are injected into the system prompt, along with the last 3 conversation turns for memory, and sent to the chat LLM.

## Database Schema

The data model is organized around organisations, users, and meetings:

| Model | Purpose |
|---|---|
| `Organisation` | Top-level tenant. All data is scoped under an org. |
| `User` | Salesperson accounts. Each belongs to one org. Admins can register new salespeople. |
| `Customer` | Clients of a salesperson. Unique per org (`UniqueConstraint` on org + name). |
| `Meeting` | A single meeting between a salesperson and customer. Tracks status (`uploaded` → `processing` → `completed` / `failed`). |
| `MeetingAnalysis` | Stores the Agent 1 structured report as a JSON field. Used by Agent 3 for historical comparison. |
| `TranscriptReport` | Stores the raw transcript and the merged markdown report. |
| `MeetingReport` | Stores the final HTML report for email delivery and frontend display. |
| `Embedding` | Transcript chunks with 1024-d vectors (HNSW indexed) and a `SearchVectorField` (GIN indexed) for hybrid search. Metadata JSON stores org/salesperson/customer/meeting IDs for filtered retrieval. |
| `ChatSession` | Groups conversation turns. UUID primary key. |
| `ChatTurn` | Individual Q&A pairs in a chat session. Stores the query vector for future semantic memory. |

## API Endpoints

### Authentication (`/auth`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register-org` | No | Register a new organisation with an admin account |
| POST | `/auth/register-salesperson` | JWT (Admin) | Add a salesperson to the admin's org |
| POST | `/auth/login` | No | Returns access + refresh tokens |
| POST | `/auth/refresh` | No | Exchange a refresh token for a new access token |
| GET | `/auth/me` | JWT | Get the logged-in user's profile |

### Meeting Processing (`/analyse`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/analyse/report` | JWT | Submit a transcript for AI processing. Returns immediately with meeting ID. |
| GET | `/analyse/meetings` | JWT | List all meetings for the logged-in salesperson |
| GET | `/analyse/customer/{id}` | JWT | List meetings filtered by customer |
| GET | `/analyse/{id}/report` | JWT | Get the HTML report for a specific meeting |
| POST | `/analyse/{id}/report` | JWT | Edit/update a meeting's HTML report |
| POST | `/analyse/{id}/send-email` | JWT | Email the report to the customer via Brevo |

### Audio Processing (`/audio`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/audio/analyse` | JWT | Upload an audio file for transcription (Groq Whisper) + AI processing |

### Chatbot (`/chat`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/chat/ask` | JWT | Ask a question. Supports optional `customer_id`, `start_date`, `end_date`, `specific_date` filters. |
| GET | `/chat/history/{session_id}` | JWT | Get all turns in a chat session |
| GET | `/chat/sessions` | JWT | List all chat sessions for the logged-in salesperson |

## Tech Stack

* **Backend:** Django, Django Ninja Extra, Uvicorn (ASGI)
* **AI Orchestration:** LangChain, LangGraph
* **Models:** OpenRouter (Llama 3.3 70B), Gemini Pro (Fallback), Groq (GPT-OSS-120B for chat, Whisper for STT)
* **Embeddings:** VoyageAI (`voyage-3.5`, 1024 dimensions)
* **Reranking:** VoyageAI Cross-Encoder (`rerank-2`)
* **Database:** PostgreSQL with `pgvector` (HNSW index) and full-text search (GIN index)
* **Concurrency:** Python `asyncio`, `sync_to_async` for Django ORM calls
* **Email:** Brevo SMTP API with `replyTo` header for sender masking
* **Auth:** Custom JWT (access + refresh tokens) using PyJWT

## Environment Variables

Create a `.env` file in the project root:

```
SECRET_KEY=your-django-secret
DEBUG=True

DB_NAME=your_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_URL=postgresql://...

GROQ_API_KEY=your_groq_key
CEREBRAS_API_KEY=your_cerebras_key
VOYAGE_API_KEY=your_voyage_key
BREVO_API_KEY=your_brevo_key
GOOGLE_API_KEY=your_google_ai_studio_key
NVIDIA_API_KEY=your_nvidia_nim_key
OPENROUTER_API_KEY=your_openrouter_key
RECALL_API_KEY=optional_recall_ai_key
```

## Local Setup

```bash
# Clone the repo
git clone https://github.com/your-username/meeting-intelligence-platform.git
cd meeting-intelligence-platform

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up your .env file (see above)

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Start the server
uvicorn backend.asgi:application --reload
```

The API docs are available at `http://localhost:8000/api/docs` once the server is running (Django Ninja auto-generates Swagger UI).

## Lessons Learned

**Why pgvector instead of Pinecone or Weaviate?**
I didn't want to add another service to manage. PostgreSQL was already my primary database, and `pgvector` with HNSW indexing gives me vector search without a separate hosted vector DB. One database handles relational data, full-text search, and vector similarity — fewer moving parts, fewer bills.

**Why Hybrid Search instead of just vector search?**
Pure semantic search misses exact terms. If a salesperson asks "what did we discuss about Pexus?", vector search might return chunks about similar-sounding companies. Adding BM25 keyword search and fusing results with RRF catches exact matches that semantic search alone would miss.

**Why asyncio background tasks instead of Celery?**
Celery needs a Redis broker, which means another paid service on Render. `asyncio.create_task` runs the LangGraph pipeline directly on the event loop — no extra infrastructure. The tradeoff is that if the server restarts mid-processing, the task is lost. For my current scale, that's acceptable.

**Why sync_to_async for Django ORM?**
Django's ORM has async methods (`aget`, `acreate`, etc.) but they use `CurrentThreadExecutor` internally. When you run them inside an `asyncio.create_task` background task, they deadlock because the background task isn't on the main thread. Wrapping ORM calls in `@sync_to_async(thread_sensitive=False)` runs them in a proper thread pool and avoids the deadlock entirely.

## Current Status

The core pipeline is functional: it processes transcripts asynchronously, generates structured meeting analyses, stores vector embeddings for semantic search, and triggers email reports. The chatbot retrieves and answers questions using hybrid search with cross-encoder reranking.

Next steps: building a fully automatic pipeline where meetings are captured and processed without manual transcript uploads.
