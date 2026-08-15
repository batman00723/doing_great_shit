import os
from typing import List, Tuple
from langchain_experimental.text_splitter import SemanticChunker
from langchain_voyageai import VoyageAIEmbeddings
from backend.config import settings

class RAGService:
    def __init__(self):
        self.embedder = VoyageAIEmbeddings(
            model="voyage-3.5", 
            voyage_api_key=settings.voyage_api_key.get_secret_value()
        )
        
        # The SemanticChunker uses the embedder to find meaning shifts.
        # "percentile" breakpoint will split the text whenever it detects a 
        # massive shift in topic compared to the surrounding sentences.
        self.chunker = SemanticChunker(
            self.embedder,
            breakpoint_threshold_type="percentile"
        )
        
    def chunk_and_embed_text(self, text: str, semantic_header: str) -> Tuple[List[str], List[List[float]]]:
        """
        Takes a raw text (transcript) and a semantic metadata header.
        Returns a tuple: (list of enriched text strings, list of 1024-d vector embeddings)
        """
        if not text.strip():
            return [], []

        # Do Semantic Chunking using a embedding model
        raw_chunks = self.chunker.create_documents([text])
        
        # Inject Metadata Header (semantic header)
        enriched_texts = []
        for chunk in raw_chunks:
            # We glue the header to the beginning of the chunk's text
            injected_text = semantic_header + chunk.page_content
            enriched_texts.append(injected_text)
            
    
        vectors = self.embedder.embed_documents(enriched_texts)
        
        return enriched_texts, vectors

    def embed_query(self, query: str) -> List[float]:
        """
        Takes a raw user query string (e.g., from the Chatbot API).
        Returns a single 1024-d vector embedding for vector database search.
        """
        if not query.strip():
            return []
            
        return self.embedder.embed_query(query)
