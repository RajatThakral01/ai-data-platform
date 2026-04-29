"""
rag_query.py - Fetching RAG context for queries.
"""
import logging
from . import embedder
from . import vector_store

logger = logging.getLogger(__name__)

def get_context(question: str, session_id: str | None, top_k: int = 5) -> tuple[str, list[dict]]:
    """
    Retrieve formatted context for a user question.
    Returns:
        context_str: Formatted string of relevant chunks.
        chunks: List of raw retrieved chunk dicts for UI display.
    """
    try:
        query_meta = embedder.embed_query_with_metadata(question)
        if not query_meta or not query_meta.get("embedding"):
            return "", []

        results: list[dict] = []
        if session_id:
            results = vector_store.hybrid_search(
                session_id=session_id,
                query_embedding=query_meta["embedding"],
                keywords=query_meta["keywords"],
                top_k=top_k,
            )

            if not results:
                results = vector_store.retrieve(
                    session_id=session_id,
                    query_embedding=query_meta["embedding"],
                    top_k=top_k,
                )

        if not results:
            return "", []

        formatted_parts = []
        for res in results:
            doc = res.get("document", "")
            page_num = "?"
            metadata = res.get("metadata") or {}
            if isinstance(metadata, dict) and metadata.get("page_num") is not None:
                page_num = metadata.get("page_num")
            formatted_parts.append(f"- [Page {page_num}] {doc}")

        context_str = "Relevant data context:\n" + "\n".join(formatted_parts)
        return context_str, results
    except Exception as e:
        logger.error(f"Failed to get RAG context: {e}")
        return "", []

def generate_query_summary(question: str, context_str: str, answer: str) -> str:
    return f"Query: {question[:100]}... | Answer summary: {answer[:200]}..."

def get_context_legacy(question: str, filename: str | None = None, cross_dataset: bool = False) -> tuple[str, list[dict]]:
    if not filename and not cross_dataset:
        return "", []
    return get_context(question, session_id=None)
