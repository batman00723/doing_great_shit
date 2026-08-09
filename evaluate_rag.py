"""
RAGAS Offline Evaluation Script
================================
Runs 15 real test questions (derived from actual ingested transcripts)
against the live RAG pipeline and produces a scored evaluation report.

Usage:
    python evaluate_rag.py

Output:
    - Scorecard printed to the terminal
    - Detailed per-question results saved to ragas_results.csv
"""

import os
import sys
import django

# ── Django Setup ─────────────────────────────────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

# ── Patch for Ragas + LangChain version mismatch ──────────────────────────────
import sys
import time
import langchain_google_vertexai
import langchain_community.chat_models
sys.modules['langchain_community.chat_models.vertexai'] = langchain_google_vertexai

# ── Imports ───────────────────────────────────────────────────────────────────
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, context_precision, context_recall
from ragas.llms import LangchainLLMWrapper
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from myapi.services.rag_services import RAGService
from myapi.services.hybrid_search import perform_hybrid_search
from myapi.services.rrf import reciprocal_rank_fusion
from myapi.services.reranker import rerank_chunks
from myapi.agent.llm import ChatLLMService
from backend.config import settings


# ── Test Dataset ──────────────────────────────────────────────────────────────
# 15 questions derived directly from the two ingested meeting transcripts.
# ground_truth is the ideal answer used to compute Context Recall.

TEST_CASES = [
    # ── Meeting 2: Board / Fundraising Meeting ────────────────────────────────
    {
        "question": "What is the forecasted annual recurring revenue by end of fiscal year?",
        "ground_truth": "The company is forecasting approximately $40 million in annual recurring revenue by the end of the fiscal year."
    },
    {
        "question": "What is the expected valuation range for the upcoming fundraising round?",
        "ground_truth": "The expected valuation range is between $180 million and $220 million, based on benchmarking comparable SaaS transactions."
    },
    {
        "question": "How much capital does the company plan to raise and what is the dilution impact?",
        "ground_truth": "The company plans to raise between $25 million and $30 million, with dilution remaining within the acceptable threshold."
    },
    {
        "question": "What are the three target markets for the Southeast Asia expansion?",
        "ground_truth": "The three target markets for Southeast Asia expansion are Singapore, Indonesia, and Vietnam."
    },
    {
        "question": "Why does Singapore appear to be the easiest entry point for expansion?",
        "ground_truth": "Singapore appears to be the easiest entry point due to regulatory clarity."
    },
    {
        "question": "Why does Vietnam require additional work before market entry?",
        "ground_truth": "Vietnam requires additional legal due diligence before market entry."
    },
    {
        "question": "What are the biggest operational risks for the Southeast Asia expansion?",
        "ground_truth": "The primary concerns are local compliance requirements, hiring experienced regional sales leaders, maintaining customer support quality during rapid expansion, and fluctuating customer acquisition costs during the first twelve months."
    },
    {
        "question": "What happened to the EBITDA margin over the last two quarters?",
        "ground_truth": "The EBITDA margin improved from 14% to 19% over the last two quarters."
    },
    {
        "question": "What are Sarah Chen's action items from the board meeting?",
        "ground_truth": "Sarah Chen committed to finalizing the valuation benchmarks, updating the financial model, and preparing an initial investor target list by Friday."
    },
    {
        "question": "What did Emily Wong commit to doing before next week?",
        "ground_truth": "Emily Wong committed to circulating the complete Southeast Asia market assessment and coordinating meetings with external legal advisors by next week."
    },
    {
        "question": "What is the estimated total fundraising timeline?",
        "ground_truth": "The fundraising timeline is approximately four to six weeks to prepare the data room, financial model, and investor presentation, followed by another eight to ten weeks to complete the process after outreach begins."
    },
    {
        "question": "What type of investors are being considered and what approach was recommended?",
        "ground_truth": "Both strategic investors and traditional growth equity funds are being considered. Sarah Chen recommended a balanced approach, noting that strategic investors could accelerate distribution partnerships while financial investors offer cleaner governance structures."
    },
    {
        "question": "How much additional cloud infrastructure investment might be needed?",
        "ground_truth": "If customer growth exceeds projections, approximately $2 million in additional cloud infrastructure investment may be needed over the next year."
    },
    # ── Meeting 1: PIXIS Product Strategy Meeting ────────────────────────────
    {
        "question": "What is the hybrid software approach being developed for PIXIS?",
        "ground_truth": "PIXIS is developing a hybrid software where users can either use it as traditional software by choosing variables themselves, or interact with an LLM assistant that is trained on the entire system to fill out different parameters through a natural conversation."
    },
    {
        "question": "What tasks can the LLM assistant help with inside PIXIS?",
        "ground_truth": "The LLM assistant can help with tasks such as ICP definition, starting campaigns, setting up different messagings in the campaigns, and other related actions within PIXIS."
    },
]


# ── Pipeline Runner ───────────────────────────────────────────────────────────
def run_pipeline_with_context(query: str):
    """
    Runs the full RAG pipeline for a single question.
    Returns (answer, top_5_chunks) so RAGAS can evaluate both.
    """
    rag_service = RAGService()
    llm_service = ChatLLMService()

    query_vector = rag_service.embed_query(query)
    if not query_vector:
        return None, []

    semantic_results, keyword_results = perform_hybrid_search(
        query=query,
        query_embedding=query_vector,
        top_k=10
    )

    if not semantic_results and not keyword_results:
        return None, []

    fused_chunks = reciprocal_rank_fusion(
        vector_results=semantic_results,
        keyword_results=keyword_results
    )

    top_5_chunks = rerank_chunks(
        query=query,
        documents=fused_chunks,
        top_k=5
    )

    if not top_5_chunks:
        return None, []

    context_text = "\n\n---\n\n".join(top_5_chunks)

    system_prompt = f"""You are an advanced Meeting Intelligence Chatbot.
Your job is to answer the user's question using ONLY the provided meeting excerpts below.
You must not hallucinate. If the excerpts do not contain the answer, politely state you do not have enough information.

<EXCERPTS>
{context_text}
</EXCERPTS>"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=query)
    ]

    try:
        response = llm_service.invoke(messages)
        return response.content, top_5_chunks
    except Exception as e:
        print(f"  LLM error: {e}")
        return None, top_5_chunks


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("   RAGAS Evaluation - Meeting Intelligence Platform")
    print("=" * 60)
    print(f"\nRunning {len(TEST_CASES)} test questions against your live RAG pipeline...\n")

    questions      = []
    answers        = []
    contexts       = []
    ground_truths  = []
    skipped        = 0

    for i, case in enumerate(TEST_CASES):
        q  = case["question"]
        gt = case["ground_truth"]
        print(f"[{i+1:02d}/{len(TEST_CASES)}] {q[:70]}...")

        answer, context = run_pipeline_with_context(q)

        if answer and context:
            questions.append(q)
            answers.append(answer)
            contexts.append(context)
            ground_truths.append(gt)
            print(f"         Retrieved ({len(context)} chunks)\n")
        else:
            skipped += 1
            print(f"         Skipped - no answer or empty context\n")
            
        # Voyage AI free tier has a 3 RPM limit (1 request per 20 seconds)
        # We sleep to prevent rate limiting.
        if i < len(TEST_CASES) - 1:
            print("         [Sleeping 21s to respect Voyage AI free tier rate limits...]")
            time.sleep(21)

    print(f"\n{len(questions)}/{len(TEST_CASES)} questions processed  |  {skipped} skipped\n")

    if not questions:
        print("No results to evaluate. Ensure your DB has embeddings.")
        print("Run the /api_v1/analyse/report endpoint first to ingest a transcript.")
        return

    # ── Build RAGAS Dataset ───────────────────────────────────────────────────
    dataset = Dataset.from_dict({
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts,
        "ground_truth": ground_truths,
    })

    # ── Configure Groq as the Judge LLM ──────────────────────────────────────
    judge_llm = LangchainLLMWrapper(ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.groq_api_key.get_secret_value()
    ))

    print("Running RAGAS evaluation (this may take 3-5 minutes)...\n")

    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            context_precision,
            context_recall,
        ],
        llm=judge_llm,
    )

    # ── Print Scorecard ───────────────────────────────────────────────────────
    df = result.to_pandas()

    faith   = df['faithfulness'].mean()
    prec    = df['context_precision'].mean()
    rec     = df['context_recall'].mean()
    overall = (faith + prec + rec) / 3

    print("\n" + "=" * 60)
    print("            RAGAS EVALUATION SCORECARD")
    print("=" * 60)
    print(f"  Faithfulness       : {faith:.4f}   (hallucination resistance)")
    print(f"  Context Precision  : {prec:.4f}   (retrieved the right chunks)")
    print(f"  Context Recall     : {rec:.4f}   (missed no important chunks)")
    print("-" * 60)
    print(f"  Overall RAG Score  : {overall:.4f}")
    print("=" * 60)

    # ── Save Detailed Results ─────────────────────────────────────────────────
    df.to_csv("ragas_results.csv", index=False)
    print(f"\n  Detailed per-question results saved to: ragas_results.csv\n")


if __name__ == "__main__":
    main()
