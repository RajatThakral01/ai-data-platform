"""
embedder.py - Sentence transformer embedding functionality.
"""
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Model name for sentence transformers
MODEL_NAME = "all-MiniLM-L6-v2"

_model: Any | None = None

def _get_model() -> Any:
    """Load and cache the sentence-transformer model in a module-level variable."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def _format_numeric_stats(series: pd.Series) -> dict[str, float | int]:
    stats = series.dropna()
    if stats.empty:
        return {"min": float("nan"), "max": float("nan"), "mean": float("nan"), "nulls": int(series.isna().sum())}
    return {
        "min": float(stats.min()),
        "max": float(stats.max()),
        "mean": float(stats.mean()),
        "nulls": int(series.isna().sum()),
    }

def _format_sample_values(series: pd.Series, limit: int = 3) -> list[str]:
    values = series.dropna().astype(str).unique().tolist()
    return values[:limit]

def embed_dataframe(df: pd.DataFrame, filename: str) -> list[dict]:
    """
    Create page-based chunks (grouped by columns) and generate embeddings.
    Returns a list of dicts with text, embedding, metadata, and page_num.
    """
    try:
        model = _get_model()

        if df.empty or df.columns.empty:
            return []

        all_cols = [str(col) for col in df.columns]
        numeric_cols = df.select_dtypes(include="number").columns.astype(str).tolist()
        categorical_cols = [col for col in all_cols if col not in numeric_cols]

        numeric_summary = []
        for col in numeric_cols:
            series = pd.to_numeric(df[col], errors="coerce")
            stats = _format_numeric_stats(series)
            numeric_summary.append({"col": col, "mean": stats["mean"], "std": float(series.dropna().std()) if not series.dropna().empty else float("nan")})
        numeric_summary.sort(key=lambda item: (item["mean"] is not None, item["mean"]))

        top_numeric = numeric_summary[:3]
        key_stats_parts = []
        for item in top_numeric:
            key_stats_parts.append(f"{item['col']}: mean={item['mean']}, std={item['std']}")

        summary_text = (
            f"Dataset: {filename} | Rows: {len(df)} | Columns: {', '.join(all_cols)}\n"
            f"Numeric cols: {', '.join(numeric_cols) if numeric_cols else 'None'} | "
            f"Categorical cols: {', '.join(categorical_cols) if categorical_cols else 'None'}\n"
            f"Key stats: {', '.join(key_stats_parts) if key_stats_parts else 'None'}"
        )

        chunks: list[dict] = [
            {
                "text": summary_text,
                "embedding": model.encode(summary_text, show_progress_bar=False).tolist(),
                "metadata": {"page_num": 0, "columns": all_cols, "chunk_type": "summary"},
                "page_num": 0,
            }
        ]

        page_size = 5
        pages = [all_cols[i:i + page_size] for i in range(0, len(all_cols), page_size)]

        for page_index, page_cols in enumerate(pages, start=1):
            stats_lines = []
            sample_lines = []
            for col in page_cols:
                series = df[col]
                if col in numeric_cols:
                    numeric_series = pd.to_numeric(series, errors="coerce")
                    stats = _format_numeric_stats(numeric_series)
                    stats_lines.append(
                        f"{col}: min={stats['min']}, max={stats['max']}, mean={stats['mean']}, nulls={stats['nulls']}"
                    )
                else:
                    nulls = int(series.isna().sum())
                    unique_count = int(series.dropna().nunique())
                    stats_lines.append(f"{col}: unique={unique_count}, nulls={nulls}")

                samples = _format_sample_values(series)
                sample_lines.append(f"{col}: [{', '.join(samples)}]" if samples else f"{col}: []")

            page_text = (
                f"Page {page_index} | Columns: {', '.join(page_cols)}\n"
                f"Stats: {'; '.join(stats_lines)}\n"
                f"Sample values: {'; '.join(sample_lines)}"
            )

            chunks.append(
                {
                    "text": page_text,
                    "embedding": model.encode(page_text, show_progress_bar=False).tolist(),
                    "metadata": {"page_num": page_index, "columns": page_cols, "chunk_type": "page"},
                    "page_num": page_index,
                }
            )

        return chunks
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

def embed_query_with_metadata(question: str) -> dict | None:
    stopwords = {
        "what", "is", "the", "a", "an", "of", "in",
        "for", "how", "many", "which", "where", "when", "are",
        "show", "me", "find", "get",
    }
    try:
        embedding = embed_query(question)
        if embedding is None:
            return None
        keywords = [word.strip().lower() for word in question.split() if word.strip().lower() not in stopwords]
        return {"embedding": embedding, "question": question, "keywords": keywords}
    except Exception as e:
        logger.error(f"Failed to embed query with metadata: {e}")
        return None
