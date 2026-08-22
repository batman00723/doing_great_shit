from myapi.models import Embedding, User, Organisation
from pgvector.django import CosineDistance
from django.contrib.postgres.search import SearchQuery
import logging
logger = logging.getLogger(__name__) 

async def perform_hybrid_search(
    query: str, 
    query_embedding: list[float], 
    user,
    top_k: int = 10,
    customer_id: int = None,
    start_date: str = None, 
    end_date: str = None,
    specific_date: str = None
):
    """
    Executes a hybrid search on PostgreSQL.
    Filters by the user's Organisation and identity.
    Returns two lists of Embedding objects: (semantic_results, keyword_results)
    """

    org_id = user.organisation_id
    salesperson_id = user.id

    logger.debug(f"Organisation {org_id}, SalesPerson: {salesperson_id}")

    if not org_id or not salesperson_id:
        raise ValueError("Database is missing initial Organisation or User.")

    # these filters are done to narrow down teh scope for the search semantic and keyword seach for better accuracy and not get other customer and salesperosn results
    dynamic_filters = {
        "metadata__organisation_id": org_id,
        "metadata__salesperson_id": salesperson_id
    }

    # Optional: narrow search to a specific customer
    if customer_id:
        dynamic_filters["metadata__customer_id"] = customer_id

    # 3. Add Optional Date Filters
    # Dates should be passed as ISO format strings (e.g., '2026-08-06')
    if specific_date:
        # Match any time on this specific day
        dynamic_filters["metadata__meeting_date__startswith"] = specific_date
    else:
        if start_date:
            dynamic_filters["metadata__meeting_date__gte"] = start_date
        if end_date:
            dynamic_filters["metadata__meeting_date__lte"] = end_date

    # 4. Apply Filters to Base Query
    base_query = Embedding.objects.filter(**dynamic_filters)



    # Calculate similarity distance → name it distance → sort by it → take the closest top_k embeddings. alias creates a temp distance
    semantic_results = [ 
        item async for item in 
        base_query.alias(
            distance=CosineDistance('vector', query_embedding)
        ).order_by('distance')[:top_k]
    ]
    

   

    # Uses PostgreSQL FTS against the chunk_search
    keyword_results = [

    item async for item in
        base_query.filter(
            chunk_search=SearchQuery(query)
        )[:top_k]
    ]
    

    return semantic_results, keyword_results
