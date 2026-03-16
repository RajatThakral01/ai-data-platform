"""
llm_logger.py - SQLite logger for LLM Observability.
"""

from __future__ import annotations

import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Derive DB path to be in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "llm_logs.db"

def init_db() -> None:
    """Initialize the SQLite database and create the schema if it doesn't exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS llm_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    module_name TEXT,
                    model_used TEXT,
                    latency_ms REAL,
                    estimated_prompt_tokens INTEGER,
                    estimated_response_tokens INTEGER,
                    success BOOLEAN,
                    fallback_used BOOLEAN,
                    error_message TEXT,
                    session_id TEXT,
                    feedback INTEGER
                )
            ''')
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize LLM logger database: {e}")

# Initialize DB on import
init_db()

def estimate_tokens(text: str | None) -> int:
    """Estimate tokens using a rough multiplier."""
    if not text:
        return 0
    return int(len(text.split()) * 1.3)

def log_call(
    module_name: str,
    model_used: str,
    latency_ms: float,
    prompt: str | None,
    response: str | None,
    success: bool,
    fallback_used: bool,
    error_message: str | None,
    session_id: str | None
) -> None:
    """Log an LLM call to the SQLite database. Fails silently."""
    try:
        prompt_tokens = estimate_tokens(prompt)
        response_tokens = estimate_tokens(response)
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO llm_logs (
                    timestamp, module_name, model_used, latency_ms, 
                    estimated_prompt_tokens, estimated_response_tokens, 
                    success, fallback_used, error_message, session_id, feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp, module_name, model_used, latency_ms,
                prompt_tokens, response_tokens,
                success, fallback_used, error_message, session_id, None
            ))
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to log LLM call: {e}")

def get_all_logs(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve the most recent logs as a list of dictionaries."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM llm_logs ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to retrieve logs: {e}")
        return []

def get_summary_stats() -> dict[str, Any]:
    """Calculate and return summary statistics from the logs."""
    stats = {
        "total_calls": 0,
        "avg_latency_ms": 0.0,
        "success_rate_pct": 0.0,
        "fallback_rate_pct": 0.0,
        "calls_per_module": {},
        "avg_latency_per_model": {}
    }
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Total calls
            cursor.execute('SELECT COUNT(*) FROM llm_logs')
            stats["total_calls"] = cursor.fetchone()[0] or 0
            
            if stats["total_calls"] > 0:
                # Average latency
                cursor.execute('SELECT AVG(latency_ms) FROM llm_logs WHERE latency_ms IS NOT NULL')
                stats["avg_latency_ms"] = cursor.fetchone()[0] or 0.0
                
                # Success rate
                cursor.execute('SELECT COUNT(*) FROM llm_logs WHERE success = 1')
                success_count = cursor.fetchone()[0] or 0
                stats["success_rate_pct"] = (success_count / stats["total_calls"]) * 100
                
                # Fallback rate
                cursor.execute('SELECT COUNT(*) FROM llm_logs WHERE fallback_used = 1')
                fallback_count = cursor.fetchone()[0] or 0
                stats["fallback_rate_pct"] = (fallback_count / stats["total_calls"]) * 100
                
                # Calls per module
                cursor.execute('SELECT module_name, COUNT(*) FROM llm_logs GROUP BY module_name')
                stats["calls_per_module"] = {row[0] if row[0] else "unknown": row[1] for row in cursor.fetchall()}
                
                # Avg latency per model
                cursor.execute('SELECT model_used, AVG(latency_ms) FROM llm_logs WHERE model_used IS NOT NULL AND latency_ms IS NOT NULL GROUP BY model_used')
                stats["avg_latency_per_model"] = {row[0]: row[1] for row in cursor.fetchall()}
                
    except Exception as e:
        logger.error(f"Failed to calculate summary stats: {e}")
        
    return stats

def update_feedback(log_id: int, feedback: int) -> None:
    """Update the feedback rating (1-5) for a specific log entry."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE llm_logs SET feedback = ? WHERE id = ?
            ''', (feedback, log_id))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update feedback: {e}")

def clear_logs() -> None:
    """Clear all records from the log table."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM llm_logs')
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to clear logs: {e}")
