from fastapi import APIRouter, HTTPException
import sys
import os
import sqlite3
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'streamlit')))
import math

from utils.llm_logger import get_summary_stats, get_all_logs

router = APIRouter()


def find_db_path():
    """Find llm_logs.db in multiple possible locations"""
    possible_db_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'llm_logs.db'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'streamlit', 'llm_logs.db'),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'streamlit', 'llm_logs.db')),
    ]
    
    for path in possible_db_paths:
        if os.path.exists(os.path.abspath(path)):
            return os.path.abspath(path)
    
    return None


def get_db_connection():
    """Get SQLite database connection"""
    db_path = find_db_path()
    if not db_path:
        return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


@router.get("/observatory/stats")
def get_stats():
    """Get LLM observatory statistics from database"""
    try:
        stats = get_summary_stats()
        logs = get_all_logs(50)

        total_calls = stats.get("total_calls", 0)
        avg_latency = stats.get("avg_latency_ms", 0.0)
        if avg_latency is not None and isinstance(avg_latency, (int, float)) and math.isnan(avg_latency):
            avg_latency = 0.0
        success_rate = stats.get("success_rate", stats.get("success_rate_pct", 0.0))
        fallback_rate = stats.get("fallback_rate", stats.get("fallback_rate_pct", 0.0))
        calls_by_module = stats.get("calls_by_module", [])
        if not calls_by_module and "calls_per_module" in stats:
            calls_by_module = [
                {"module": k, "count": v}
                for k, v in stats.get("calls_per_module", {}).items()
            ]

        latency_over_time = [
            {
                "timestamp": row.get("timestamp"),
                "latency": float(row.get("latency_ms") or 0.0),
                "model": row.get("model_used") or "unknown"
            }
            for row in reversed(logs)
        ]

        return {
            "total_calls": total_calls,
            "success_rate": float(success_rate),
            "avg_latency": float(avg_latency),
            "fallback_rate": float(fallback_rate),
            "total_cost": 0.0,
            "calls_by_module": calls_by_module,
            "latency_over_time": latency_over_time
        }
    except Exception:
        return {
            "total_calls": 0,
            "success_rate": 0.0,
            "avg_latency": 0.0,
            "fallback_rate": 0.0,
            "total_cost": 0.0,
            "calls_by_module": [],
            "latency_over_time": []
        }


@router.get("/observatory/logs")
def get_logs(limit: int = 50):
    """Get recent LLM logs from database"""
    try:
        logs = get_all_logs(limit)
        return [
            {
                "timestamp": row.get("timestamp"),
                "module_name": row.get("module_name") or "unknown",
                "model_used": row.get("model_used") or "unknown",
                "latency_ms": float(row.get("latency_ms") or 0.0),
                "success": bool(row.get("success")),
                "fallback_used": bool(row.get("fallback_used"))
            }
            for row in reversed(logs)
        ]
    except Exception:
        return []
