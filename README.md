# Meeting Intelligence Platform

I started this project to solve a specific problem: organizations spend countless hours on calls, but extracting actionable insights, tracking historical context, and generating reports takes too much manual effort. This platform automates that entire workflow using a multi-agent AI system.

## High-Level Architecture

At its core, this is an asynchronous Python backend built with Django Ninja and served via Uvicorn. To keep the API highly responsive, the heavy AI processing is completely detached from the HTTP request cycle and handled in background tasks.

```mermaid
graph TD
    Client[Client application] -->|Uploads Audio| API[Django Ninja API]
    API -->|Instantly returns 200 OK| Client
    API -->|Spawns background task| Task[Async Background Task]
    Task --> Audio[Audio Transcription via Groq/Whisper]
    Audio --> AI[LangGraph Multi-Agent Pipeline]
    AI --> DB[(PostgreSQL + pgvector)]
    AI --> Email[Email Delivery]
```

## AI Agent Workflow (LangGraph)

The intelligence of the platform is driven by LangGraph. Instead of relying on a single large prompt, the system routes the transcript through specialized agents running in parallel. I designed it to gracefully fall back to alternative models (e.g., from OpenRouter to Gemini) if API rate limits or failures occur.

```mermaid
graph TD
    Start[Audio Transcript] --> A1[Agent 1: Structured Report]
    Start --> A2[Agent 2: Narrative Report]
    
    A1 --> A3[Agent 3: Historical Comparison]
    A2 --> A3
    
    A3 --> Merge[Merge All Reports]
    Merge --> Format[Generate Markdown & HTML]
    
    Format --> Embeddings[Chunk & Generate RAG Embeddings]
    Format --> Save[Transaction Save to Database]
    
    Embeddings --> Complete[Finish Pipeline]
    Save --> Complete
```

## RAG & Retrieval Architecture

I built a custom Retrieval-Augmented Generation (RAG) pipeline to power the chat interface. Instead of just doing a basic vector similarity search, I implemented a hybrid approach. Every chunk of transcript is injected with a "Semantic Header" (containing metadata like the organization, salesperson, and meeting details) before embedding to give the LLM better raw context. 

During retrieval, the system combines semantic vector search (via pgvector) with hard SQL metadata filtering and Full-Text Search (GIN indexing). This ensures that chatbot responses are highly relevant and strictly isolated to the correct organization and customer.

```mermaid
graph TD
    subgraph Ingestion Pipeline
        T[Transcript Text] --> Header[Inject Semantic Header]
        Header --> Chunk[Chunk Text]
        Chunk --> Embed[Generate Embeddings]
        Embed --> PG[(PostgreSQL + pgvector)]
        PG -.->|Stores| V[Vectors]
        PG -.->|Stores| M[JSON Metadata]
        PG -.->|Stores| GIN[GIN Index for Keyword Search]
    end

    subgraph Retrieval Pipeline
        Q[User Chat Query] --> QE[Embed Query]
        QE --> Search[Hybrid Search]
        Search -.->|Vector Similarity| V
        Search -.->|Strict SQL Filtering| M
        Search -.->|Full Text Match| GIN
        Search --> Context[Retrieve Top Chunks]
        Context --> LLM[LLM Generation]
        LLM --> Answer[Chatbot Response]
    end
```

## Tech Stack

* **Backend:** Django, Django Ninja Extra, Uvicorn (ASGI)
* **AI Orchestration:** LangChain, LangGraph
* **Models:** OpenRouter (Llama), Gemini (Fallback), Groq (Whisper for STT)
* **Database:** PostgreSQL with pgvector (for RAG and semantic search)
* **Concurrency:** Python asyncio, custom async database handlers (sync_to_async)

## Current Status

This project is in active development. The core multi-agent pipeline is functional: it successfully processes audio asynchronously, generates comprehensive meeting analyses, stores vector embeddings for semantic search, and triggers email reports. Future updates will focus on refining the RAG retrieval pipeline for the chatbot interface and expanding the deployment infrastructure.
