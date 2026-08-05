import voyageai
from backend.config import settings

def rerank_chunks(query: str, documents: list[str], top_k: int = 5) -> list[str]:
    """
    Uses Voyage AI's Cross-Encoder to evaluate the fused chunks against the raw query.
    Returns the absolute best `top_k` chunks as text strings.
    """
    if not documents:
        return []
    
    vo = voyageai.Client(api_key=settings.voyage_api_key.get_secret_value())

    reranking = vo.rerank(
        query=query, 
        documents=documents, 
        model="rerank-2", 
        top_k=top_k
    )
    
    # Voyage AI returns results already sorted by relevance (highest to lowest)
    # result.document contains the original text string.
    top_chunks = [result.document for result in reranking.results]
    
    return top_chunks
