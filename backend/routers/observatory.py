from fastapi import APIRouter, HTTPException
import sqlite3
import os
import math

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
    conn = get_db_connection()
    
    # Return defaults if database doesn't exist
    if conn is None:
        return {
            "total_calls": 0,
            "success_rate": 0.0,
            "avg_latency": 0.0,
            "fallback_rate": 0.0,
            "total_cost": 0.0,
            "calls_by_module": [],
            "latency_over_time": []
        }
    
    try:
        cursor = conn.cursor()
        
        # Get total calls
        cursor.execute("SELECT COUNT(*) as count FROM llm_logs")
        total_calls = cursor.fetchone()["count"] or 0
        
        # If no data, return defaults
        if total_calls == 0:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "avg_latency": 0.0,
                "fallback_rate": 0.0,
                "total_cost": 0.0,
                "calls_by_module": [],
                "latency_over_time": []
            }
        
        # Get success rate
        cursor.execute("SELECT COUNT(*) as count FROM llm_logs WHERE success = 1")
        success_count = cursor.fetchone()["count"] or 0
        success_rate = (success_count / total_calls * 100) if total_calls > 0 else 0.0
        
        # Get average latency
        cursor.execute("SELECT AVG(latency_ms) as avg_latency FROM llm_logs")
        avg_latency_row = cursor.fetchone()
        avg_latency = avg_latency_row["avg_latency"] or 0.0
        if avg_latency is not None and math.isnan(avg_latency):
            avg_latency = 0.0
        
        # Get fallback rate
        cursor.execute("SELECT COUNT(*) as count FROM llm_logs WHERE fallback_used = 1")
        fallback_count = cursor.fetchone()["count"] or 0
        fallback_rate = (fallback_count / total_calls * 100) if total_calls > 0 else 0.0
        
        # Get total cost
        cursor.execute(
            """SELECT 
                SUM(estimated_prompt_tokens * 0.000001 + estimated_response_tokens * 0.000002) as total_cost
            FROM llm_logs"""
        )
        total_cost_row = cursor.fetchone()
        total_cost = total_cost_row["total_cost"] or 0.0
        if total_cost is None:
            total_cost = 0.0
        
        # Get calls by module
        cursor.execute(
            """SELECT module_name, COUNT(*) as count 
            FROM llm_logs 
            GROUP BY module_name 
            ORDER BY count DESC"""
        )
        calls_by_module = [
            {"module": row["module_name"], "count": row["count"]}
            for row in cursor.fetchall()
        ]
        
        # Get latency over time (last 50 rows)
        cursor.execute(
            """SELECT timestamp, latency_ms, model_used 
            FROM llm_logs 
            ORDER BY id DESC 
            LIMIT 50"""
        )
        latency_over_time = [
            {
                "timestamp": row["timestamp"],
                "latency": float(row["latency_ms"]) if row["latency_ms"] is not None else 0.0,
                "model": row["model_used"] or "unknown"
            }
            for row in reversed(cursor.fetchall())
        ]
        
        return {
            "total_calls": total_calls,
            "success_rate": float(success_rate),
            "avg_latency": float(avg_latency),
            "fallback_rate": float(fallback_rate),
            "total_cost": float(total_cost),
            "calls_by_module": calls_by_module,
            "latency_over_time": latency_over_time
        }
        
    except Exception as e:
        # Return defaults on error
        return {
            "total_calls": 0,
            "success_rate": 0.0,
            "avg_latency": 0.0,
            "fallback_rate": 0.0,
            "total_cost": 0.0,
            "calls_by_module": [],
            "latency_over_time": []
        }
    finally:
        if conn:
            conn.close()


@router.get("/observatory/logs")
def get_logs(limit: int = 50):
    """Get recent LLM logs from database"""
    conn = get_db_connection()
    
    # Return empty list if database doesn't exist
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT 
                timestamp, 
                module_name, 
                model_used, 
                latency_ms, 
                success, 
                fallback_used
            FROM llm_logs 
            ORDER BY id DESC 
            LIMIT ?""",
            (limit,)
        )
        
        logs = [
            {
                "timestamp": row["timestamp"],
                "module_name": row["module_name"] or "unknown",
                "model_used": row["model_used"] or "unknown",
                "latency_ms": float(row["latency_ms"]) if row["latency_ms"] is not None else 0.0,
                "success": bool(row["success"]),
                "fallback_used": bool(row["fallback_used"])
            }
            for row in reversed(cursor.fetchall())
        ]
        
        return logs
        
    except Exception as e:
        # Return empty list on error
        return []
    finally:
        if conn:
            conn.close()
