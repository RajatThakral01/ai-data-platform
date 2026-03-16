"""
rag_query.py - Fetching RAG context for queries.
"""
import logging
from . import embedder
from . import vector_store

logger = logging.getLogger(__name__)

def get_context(question: str, filename: str | None = None, cross_dataset: bool = False) -> tuple[str, list[dict]]:
    """
    Retrieve formatted context for a user question.
    Returns:
        context_str: Formatted string of relevant chunks.
        chunks: List of raw retrieved chunk dicts for UI display.
    """
    try:
        query_embedding = embedder.embed_query(question)
        if not query_embedding:
            return "", []

        if cross_dataset:
            logger.info("Retrieving context across ALL datasets.")
            results = vector_store.retrieve_across_all(query_embedding, top_k=5)
        elif filename:
            logger.info(f"Retrieving context for dataset: {filename}")
            results = vector_store.retrieve(filename, query_embedding, top_k=5)
        else:
            logger.info("No filename and no cross_dataset flag. Cannot retrieve context.")
            return "", []

        if not results:
            return "", []

        # Format retrieved chunks
        formatted_parts = []
        for i, res in enumerate(results):
            doc = res.get("document", "")
            source = res.get("source", "unknown")
            formatted_parts.append(f"- [Source: {source}] {doc}")

        context_str = "Relevant data rows for context:\n" + "\n".join(formatted_parts)
        return context_str, results
        
    except Exception as e:
        logger.error(f"Failed to get RAG context: {e}")
        return "", []
