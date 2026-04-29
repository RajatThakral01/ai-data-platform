from fastapi import APIRouter
import sys
import os
import logging
import numpy as np

try:
    from db.supabase_client import get_supabase
    _supabase_available = True
except ImportError:
    _supabase_available = False

logger = logging.getLogger(__name__)
router = APIRouter()


def _cluster_queries(questions: list[str], embeddings: list[list[float]]) -> dict[int, list[str]]:
    """Cluster questions using HDBSCAN. Returns dict of cluster_id -> questions."""
    if len(questions) < 3:
        return {0: questions}
    try:
        import hdbscan
        import numpy as np
        X = np.array(embeddings)
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric="euclidean")
        labels = clusterer.fit_predict(X)
        clusters: dict[int, list[str]] = {}
        for label, question in zip(labels, questions):
            key = int(label)
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(question)
        return clusters
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        return {0: questions}


@router.get("/query-clusters")
def get_query_clusters(session_id: str | None = None, limit: int = 50):
    """
    Fetch recent NL queries from Supabase, cluster them with HDBSCAN,
    and return clusters with representative questions (people also asked).
    """
    if not _supabase_available:
        return {"clusters": [], "total_queries": 0, "message": "Supabase not available"}

    try:
        supabase = get_supabase()
        if not supabase:
            return {"clusters": [], "total_queries": 0}

        query = supabase.table("nl_query_history") \
            .select("question, query_type, embedding, session_id") \
            .order("created_at", desc=True) \
            .limit(limit)

        if session_id:
            query = query.eq("session_id", session_id)

        result = query.execute()
        rows = result.data or []

        if not rows:
            return {"clusters": [], "total_queries": 0}

        questions = [r["question"] for r in rows]
        query_types = [r.get("query_type", "general") for r in rows]
        embeddings = [r.get("embedding") for r in rows]

        has_embeddings = all(e is not None for e in embeddings)

        if has_embeddings and len(questions) >= 3:
            clusters_raw = _cluster_queries(questions, embeddings)
        else:
            clusters_raw = {}
            for q, qt in zip(questions, query_types):
                if qt not in clusters_raw:
                    clusters_raw[qt] = []
                clusters_raw[qt].append(q)

        clusters_output = []
        for cluster_id, cluster_questions in clusters_raw.items():
            label = "noise" if cluster_id == -1 else f"cluster_{cluster_id}"
            clusters_output.append({
                "cluster_id": cluster_id,
                "label": label,
                "questions": cluster_questions,
                "count": len(cluster_questions),
                "representative": cluster_questions[0],
            })

        clusters_output.sort(key=lambda x: x["count"], reverse=True)

        return {
            "clusters": clusters_output,
            "total_queries": len(questions),
            "clustered": has_embeddings,
        }

    except Exception as e:
        logger.error(f"Failed to get query clusters: {e}")
        return {"clusters": [], "total_queries": 0, "error": str(e)}
