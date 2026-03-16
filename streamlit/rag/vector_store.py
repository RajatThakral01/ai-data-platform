"""
vector_store.py - Persistent ChromaDB client for vector storage and retrieval.
"""
import chromadb
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

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
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    # Ensure it starts and ends with alphanumeric
    sanitized = re.sub(r'^[^a-zA-Z0-9]+', 'a_', sanitized)
    sanitized = re.sub(r'[^a-zA-Z0-9]+$', '_z', sanitized)
    # Length constraints
    if len(sanitized) < 3:
        sanitized = sanitized.ljust(3, 'x')
    if len(sanitized) > 63:
        sanitized = sanitized[:63]
    return sanitized

def store_dataset(filename: str, chunks_with_embeddings: list[tuple[str, list[float]]]) -> bool:
    """
    Store text chunks and their embeddings into a ChromaDB collection named after the filename.
    """
    try:
        if not chunks_with_embeddings:
            logger.warning(f"No chunks to store for dataset {filename}")
            return False

        client = _get_client()
        collection_name = _sanitize_name(filename)
        
        # Get or create collection
        collection = client.get_or_create_collection(
            name=collection_name, 
            metadata={"filename": filename}
        )
        
        # Prepare data for upsert
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        for i, (chunk_text, embedding) in enumerate(chunks_with_embeddings):
            ids.append(f"{collection_name}_chunk_{i}")
            documents.append(chunk_text)
            embeddings.append(embedding)
            metadatas.append({"source": filename, "chunk_index": i})
            
        # ChromaDB can handle batches, for <1000 items doing it all at once is fine
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"Stored {len(ids)} chunks in collection {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to store dataset {filename} in ChromaDB: {e}")
        return False

def retrieve(filename: str, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """
    Retrieve top_k most similar chunks from a specific dataset's collection.
    Returns list of dicts: {"document": text, "source": filename, "distance": float}
    """
    try:
        client = _get_client()
        collection_name = _sanitize_name(filename)
        
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            logger.warning(f"Collection {collection_name} does not exist.")
            return []
            
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count())
        )
        
        retrieved = []
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            
            for doc, meta, dist in zip(docs, metadatas, distances):
                retrieved.append({
                    "document": doc,
                    "source": meta.get("source", filename),
                    "distance": dist
                })
        return retrieved
    except Exception as e:
        logger.error(f"Failed to retrieve from {filename}: {e}")
        return []

def retrieve_across_all(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """
    Search across all collections and return the overall top_k most similar chunks.
    """
    try:
        client = _get_client()
        collections = client.list_collections()
        
        all_results = []
        for collection in collections:
            # collection is an object (Collection class) in chromadb v0.5.0
            if collection.count() == 0:
                continue
                
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count())
            )
            
            if results and results.get("documents") and results["documents"][0]:
                docs = results["documents"][0]
                metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                distances = results["distances"][0] if results.get("distances") else [float('inf')] * len(docs)
                
                for doc, meta, dist in zip(docs, metadatas, distances):
                    all_results.append({
                        "document": doc,
                        "source": meta.get("source", "unknown"),
                        "distance": dist
                    })
                    
        # Sort by distance (lower is better for most distance metrics) and take top_k
        all_results.sort(key=lambda x: x["distance"])
        return all_results[:top_k]
    except Exception as e:
        logger.error(f"Failed to retrieve across all datasets: {e}")
        return []

def list_indexed_datasets() -> list[str]:
    """Return a list of original filenames of indexed datasets."""
    try:
        client = _get_client()
        collections = client.list_collections()
        dataset_names = []
        for collection in collections:
            metadata = collection.metadata or {}
            filename = metadata.get("filename")
            if filename:
                dataset_names.append(filename)
            else:
                dataset_names.append(collection.name)
        return sorted(dataset_names)
    except Exception as e:
        logger.error(f"Failed to list indexed datasets: {e}")
        return []

def delete_dataset(filename: str) -> bool:
    """Delete a dataset's collection from ChromaDB."""
    try:
        client = _get_client()
        collection_name = _sanitize_name(filename)
        client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete dataset {filename}: {e}")
        return False
