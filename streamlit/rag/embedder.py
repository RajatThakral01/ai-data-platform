"""
embedder.py - Sentence transformer embedding functionality.
"""
import streamlit as st
import pandas as pd
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

# Model name for sentence transformers
MODEL_NAME = "all-MiniLM-L6-v2"

def _get_model() -> Any:
    """Load and cache the sentence-transformer model in st.session_state."""
    if "sentence_transformer_model" not in st.session_state:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        st.session_state["sentence_transformer_model"] = SentenceTransformer(MODEL_NAME)
    return st.session_state["sentence_transformer_model"]

def embed_dataframe(df: pd.DataFrame, filename: str) -> list[tuple[str, list[float]]]:
    """
    Convert a dataframe into text chunks and generate embeddings.
    Samples up to 1000 rows if the dataframe is large.
    Returns a list of (chunk_text, embedding) tuples.
    """
    try:
        model = _get_model()
        
        # Sample if too large
        if len(df) > 1000:
            logger.info(f"Sampling 1000 rows from {filename} for embedding out of {len(df)} total.")
            # We want reproducible sampling if possible, so we use a seed
            sample_df = df.sample(n=1000, random_state=42)
        else:
            sample_df = df

        chunks = []
        # Create text representation of each row
        for idx, row in sample_df.iterrows():
            row_str = f"Row {idx}: " + ", ".join(f"{col}: {val}" for col, val in row.items())
            chunks.append(row_str)

        if not chunks:
            return []

        logger.info(f"Generating embeddings for {len(chunks)} chunks from {filename}...")
        embeddings = model.encode(chunks, show_progress_bar=False)
        
        return list(zip(chunks, embeddings.tolist()))
    except Exception as e:
        logger.error(f"Failed to embed dataframe {filename}: {e}")
        return []

def embed_query(question: str) -> list[float] | None:
    """Generate an embedding vector for a user query."""
    try:
        model = _get_model()
        embedding = model.encode(question, show_progress_bar=False)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return None
