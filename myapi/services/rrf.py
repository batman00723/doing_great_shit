def reciprocal_rank_fusion(vector_results, keyword_results, k=60):
    scores = {}
    chunk_map = {}
    
    # Rank 1 gets 1/(60+1), Rank 2 gets 1/(60+2)...
    for rank, chunk in enumerate(vector_results, 1):
        scores[chunk.id] = scores.get(chunk.id, 0) + 1 / (k + rank)
        chunk_map[chunk.id] = chunk.chunks
        
    for rank, chunk in enumerate(keyword_results, 1):
        scores[chunk.id] = scores.get(chunk.id, 0) + 1 / (k + rank)
        chunk_map[chunk.id] = chunk.chunks
        
    # Sort by the new fused score
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Return the actual text strings for the top 10 chunks, not just the IDs
    return [chunk_map[chunk_id] for chunk_id, _ in sorted_items[:10]]
