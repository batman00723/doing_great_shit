# LangGraph Report Generation Workflow

This diagram illustrates the exact execution flow of your LangGraph agent (`myapi/agent/graph.py`).

Notice how you have perfectly utilized **Parallel Execution (Fan-Out)** and **Synchronization (Fan-In)**. By doing this, you are significantly reducing the total time it takes to process a transcript compared to doing it linearly.

```mermaid
graph TD
    %% Define Styles
    classDef startEnd fill:#10b981,stroke:#059669,stroke-width:2px,color:white,font-weight:bold;
    classDef llmNode fill:#3b82f6,stroke:#2563eb,stroke-width:2px,color:white;
    classDef formatNode fill:#8b5cf6,stroke:#7c3aed,stroke-width:2px,color:white;
    classDef dbNode fill:#f59e0b,stroke:#d97706,stroke-width:2px,color:white;
    classDef outputNode fill:#ec4899,stroke:#db2777,stroke-width:2px,color:white;

    %% Nodes
    START([🚀 START]) ::: startEnd
    
    subgraph Parallel LLM Extraction
        S_REPORT[Agent 1: Structured Report<br/>Extracts JSON facts] ::: llmNode
        N_REPORT[Agent 2: Narrative Report<br/>Extracts summary & context] ::: llmNode
    end
    
    H_REPORT[Agent 3: Historical Report<br/>Compares with past meetings] ::: llmNode
    
    M_REPORT[Merge Report<br/>Combines Agent 1, 2, & 3 outputs] ::: formatNode

    subgraph Parallel Formatting
        C_MD[Create Markdown<br/>Formats clean text] ::: formatNode
        H_HTML[Create HTML<br/>Generates visual report] ::: formatNode
    end
    
    SAVE_DB[(Save to Database<br/>MeetingReport & TranscriptReport)] ::: dbNode
    
    subgraph Parallel Output & Processing
        EMAIL[Send Email<br/>Dispatches via Brevo] ::: outputNode
        EMBED[Generate Embeddings<br/>Chunks & Saves to pgvector] ::: dbNode
    end
    
    END([🛑 END]) ::: startEnd

    %% Edges
    START --> S_REPORT
    START --> N_REPORT
    
    S_REPORT --> H_REPORT
    N_REPORT --> H_REPORT
    
    H_REPORT --> M_REPORT
    
    M_REPORT --> C_MD
    M_REPORT --> H_HTML
    
    C_MD --> SAVE_DB
    H_HTML --> SAVE_DB
    
    SAVE_DB --> EMAIL
    SAVE_DB --> EMBED
    
    EMAIL --> END
    EMBED --> END
```

### Key Architectural Highlights:
1. **Parallel Extraction:** `Structured Report` and `Narrative Report` run at the exact same time, cutting your initial LLM wait time in half.
2. **Sync Point 1:** `Historical Report` waits for both extractions to finish so it can use them.
3. **Parallel Formatting:** Markdown and HTML generation happen simultaneously.
4. **Sync Point 2:** `Save to DB` waits for both formatting tasks to finish so it has all the data it needs to write the row.
5. **Parallel Output:** Sending the email and generating the complex vector embeddings happen at the same time, without blocking each other.
