"""
vector_store.py - Supabase pgvector storage and retrieval with ChromaDB fallback.
"""
import sys
import os
import logging
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))
try:
    from db.supabase_client import get_supabase
    _supabase_available = True
except ImportError:
    _supabase_available = False

logger = logging.getLogger(__name__)

def _batch(items: list[dict], size: int) -> list[list[dict]]:
    return [items[i:i + size] for i in range(0, len(items), size)]

def store_dataset(session_id: str, filename: str, chunks: list[dict]) -> bool:
    """
    Store chunk dicts in Supabase document_chunks table.
    Each chunk dict contains: text, embedding, metadata, page_num.
    """
    if not _supabase_available:
        logger.warning("Supabase unavailable, falling back to ChromaDB store_dataset.")
        return _chroma_store_dataset(session_id, filename, chunks)

    try:
        supabase = get_supabase()
        if not supabase:
            logger.warning("Supabase client not available, falling back to ChromaDB store_dataset.")
            return _chroma_store_dataset(session_id, filename, chunks)

        supabase.table("document_chunks").delete().eq("session_id", session_id).execute()

        if not chunks:
            logger.warning(f"No chunks to store for session {session_id}")
            return False

        rows = []
        for chunk in chunks:
            rows.append(
                {
                    "session_id": session_id,
                    "chunk_text": chunk["text"],
                    "embedding": chunk["embedding"],
                    "page_num": chunk["page_num"],
                    "metadata": chunk["metadata"],
                }
            )

        for batch in _batch(rows, 50):
            supabase.table("document_chunks").insert(batch).execute()

        logger.info(f"Stored {len(rows)} chunks for session {session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to store dataset for session {session_id}: {e}")
        return False

def retrieve(session_id: str, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Retrieve top_k most similar chunks for a session via Supabase RPC."""
    if not _supabase_available:
        logger.warning("Supabase unavailable, falling back to ChromaDB retrieve.")
        return _chroma_retrieve(session_id, query_embedding, top_k)

    try:
        supabase = get_supabase()
        if not supabase:
            logger.warning("Supabase client not available, falling back to ChromaDB retrieve.")
            return _chroma_retrieve(session_id, query_embedding, top_k)

        result = supabase.rpc(
            "match_chunks",
            {
                "query_embedding": query_embedding,
                "session_id_filter": session_id,
                "match_count": top_k,
            },
        ).execute()

        rows = result.data or []
        return [
            {
                "document": row.get("chunk_text"),
                "similarity": row.get("similarity"),
                "metadata": row.get("metadata"),
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to retrieve chunks for session {session_id}: {e}")
        return []

def hybrid_search(
    session_id: str,
    query_embedding: list[float],
    keywords: list[str],
    top_k: int = 5,
) -> list[dict]:
    if not _supabase_available:
        logger.warning("Supabase unavailable, falling back to ChromaDB retrieve.")
        return _chroma_retrieve(session_id, query_embedding, top_k)

    try:
        supabase = get_supabase()
        if not supabase:
            logger.warning("Supabase client not available, falling back to ChromaDB retrieve.")
            return _chroma_retrieve(session_id, query_embedding, top_k)

        semantic_results = retrieve(session_id, query_embedding, top_k=top_k)
        semantic_scored: dict[str, dict[str, Any]] = {}
        for row in semantic_results:
            doc_id = row.get("id") or row.get("metadata", {}).get("id") or row.get("document")
            if not doc_id:
                doc_id = f"semantic_{len(semantic_scored)}"
            semantic_scored[doc_id] = {
                "row": row,
                "score": 0.7 * float(row.get("similarity") or 0.0),
            }

        keyword_scored: dict[str, dict[str, Any]] = {}
        for keyword in keywords[:3]:
            response = (
                supabase.table("document_chunks")
                .select("id, chunk_text, metadata")
                .eq("session_id", session_id)
                .ilike("chunk_text", f"%{keyword}%")
                .execute()
            )
            for row in response.data or []:
                doc_id = row.get("id")
                if not doc_id:
                    continue
                if doc_id not in keyword_scored:
                    keyword_scored[doc_id] = {"row": row, "score": 0.3}
                else:
                    keyword_scored[doc_id]["score"] += 0.3

        combined: dict[str, dict[str, Any]] = {}
        for doc_id, data in semantic_scored.items():
            combined[doc_id] = {
                "document": data["row"].get("document") or data["row"].get("chunk_text"),
                "similarity": data["row"].get("similarity"),
                "metadata": data["row"].get("metadata"),
                "score": data["score"],
            }

        for doc_id, data in keyword_scored.items():
            if doc_id in combined:
                combined[doc_id]["score"] += data["score"]
            else:
                combined[doc_id] = {
                    "document": data["row"].get("chunk_text"),
                    "similarity": None,
                    "metadata": data["row"].get("metadata"),
                    "score": data["score"],
                }

        sorted_results = sorted(combined.values(), key=lambda item: item["score"], reverse=True)
        return sorted_results[:top_k]
    except Exception as e:
        logger.error(f"Failed to hybrid search for session {session_id}: {e}")
        return []

def delete_dataset(session_id: str) -> bool:
    """Delete all chunks for a session from Supabase."""
    if not _supabase_available:
        logger.warning("Supabase unavailable, falling back to ChromaDB delete_dataset.")
        return _chroma_delete_dataset(session_id)

    try:
        supabase = get_supabase()
        if not supabase:
            logger.warning("Supabase client not available, falling back to ChromaDB delete_dataset.")
            return _chroma_delete_dataset(session_id)
        supabase.table("document_chunks").delete().eq("session_id", session_id).execute()
        logger.info(f"Deleted chunks for session {session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete chunks for session {session_id}: {e}")
        return False

if not _supabase_available:
    import chromadb
    import re
    from pathlib import Path

    # Derive DB path to be in the project root
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"

    def _get_client():
        """Get or initialize the persistent ChromaDB client."""
        return chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    def _sanitize_name(name: str) -> str:
        """
        Sanitize dataset string to be a valid ChromaDB collection name.
        Rules: 3-63 chars, start/end with alpha, contain numeric/alpha/hyphens/underscores/dots.
        Consecutive dots/hyphens are not allowed, but we'll do a basic sanitization.
        """
        # Replace anything non-alphanumeric with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        # Ensure it starts and ends with alphanumeric
        sanitized = re.sub(r"^[^a-zA-Z0-9]+", "a_", sanitized)
        sanitized = re.sub(r"[^a-zA-Z0-9]+$", "_z", sanitized)
        # Length constraints
        if len(sanitized) < 3:
            sanitized = sanitized.ljust(3, "x")
        if len(sanitized) > 63:
            sanitized = sanitized[:63]
        return sanitized

    def _chroma_store_dataset(session_id: str, filename: str, chunks: list[dict]) -> bool:
        """Fallback: store chunk text and embeddings into a ChromaDB collection."""
        try:
            if not chunks:
                logger.warning(f"No chunks to store for dataset {filename}")
                return False

            client = _get_client()
            collection_name = _sanitize_name(filename)

            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"filename": filename, "session_id": session_id},
            )

            ids = []
            documents = []
            embeddings = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                ids.append(f"{collection_name}_chunk_{i}")
                documents.append(chunk["text"])
                embeddings.append(chunk["embedding"])

                # ChromaDB only allows str/int/float/bool metadata values.
                # Serialize any list/dict values to strings before upsert.
                raw_meta = chunk.get("metadata", {}) or {}
                safe_meta = {}
                for k, v in raw_meta.items():
                    if isinstance(v, list):
                        safe_meta[k] = ", ".join(str(x) for x in v)
                    elif isinstance(v, dict):
                        safe_meta[k] = str(v)
                    elif isinstance(v, (str, int, float, bool)):
                        safe_meta[k] = v
                    else:
                        safe_meta[k] = str(v)
                metadatas.append(safe_meta)

            collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            logger.info(f"Stored {len(ids)} chunks in collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to store dataset {filename} in ChromaDB: {e}")
            return False

    def _chroma_retrieve(session_id: str, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """
        Fallback: retrieve top_k most similar chunks from a dataset collection.
        Returns list of dicts: {"document": text, "source": filename, "distance": float}
        """
        try:
            client = _get_client()
            collection_name = _sanitize_name(session_id)

            try:
                collection = client.get_collection(name=collection_name)
            except Exception:
                logger.warning(f"Collection {collection_name} does not exist.")
                return []

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count()),
            )

            retrieved = []
            if results and results.get("documents") and results["documents"][0]:
                docs = results["documents"][0]
                metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

                for doc, meta, dist in zip(docs, metadatas, distances):
                    retrieved.append(
                        {
                            "document": doc,
                            "source": meta.get("source", session_id),
                            "distance": dist,
                        }
                    )
            return retrieved
        except Exception as e:
            logger.error(f"Failed to retrieve from {session_id}: {e}")
            return []

    def _chroma_delete_dataset(session_id: str) -> bool:
        """Fallback: delete a dataset's collection from ChromaDB."""
        try:
            client = _get_client()
            collection_name = _sanitize_name(session_id)
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete dataset {session_id}: {e}")
            return False
