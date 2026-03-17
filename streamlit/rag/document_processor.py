"""
document_processor.py - Process and index documents for RAG.
"""
import logging
from . import embedder
from . import vector_store

logger = logging.getLogger(__name__)

def process_and_index_dataframe(df, filename: str, session_id: str = "") -> bool:
    """
    Process a dataframe into chunks and index it for RAG.
    
    Args:
        df: The input dataframe
        filename: Name of the dataset
        session_id: Unique session identifier (optional, defaults to empty string)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Embed the dataframe into page-based chunks
        chunks = embedder.embed_dataframe(df, filename)
        if not chunks:
            logger.warning(f"No chunks generated for {filename}")
            return False
        
        # Store chunks in vector database
        success = vector_store.store_dataset(session_id, filename, chunks)
        if success:
            logger.info(f"Successfully indexed {filename} with {len(chunks)} chunks for session {session_id}")
        return success
    except Exception as e:
        logger.error(f"Failed to process and index {filename}: {e}")
        return False
