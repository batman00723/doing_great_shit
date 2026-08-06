from myapi.models import Embedding, User, Organisation
from pgvector.django import CosineDistance
from django.contrib.postgres.search import SearchQuery

def perform_hybrid_search(query: str, query_embedding: list[float], top_k: int = 10, start_date: str = None, end_date: str = None, specific_date: str = None):
    """
    Executes a hybrid search on PostgreSQL.
    Filters strictly by the first Organisation and User in the DB (mocking auth).
    Returns two lists of Embedding objects: (semantic_results, keyword_results)
    """

    org = Organisation.objects.first()
    salesperson = User.objects.first()


    print (f"Organisation {org}, SalesPerson: {salesperson}")

    if not org or not salesperson:
        raise ValueError("Database is missing initial Organisation or User.")

    dynamic_filters = {
        "metadata__organisation_id": org.id,
        "metadata__salesperson_id": salesperson.id
    }

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

    print(f"Query after filters {base_query}")

    # senamtic search
    semantic_results = list(
        base_query.alias(
            distance=CosineDistance('vector', query_embedding)
        ).order_by('distance')[:top_k]
    )

    print(f"Semantic Search Result: {semantic_results}")

    # Uses PostgreSQL FTS against the chunk_search
    keyword_results = list(
        base_query.filter(
            chunk_search=SearchQuery(query)
        )[:top_k]
    )
    print(f"Keyword Search results{keyword_results}")

    return semantic_results, keyword_results
