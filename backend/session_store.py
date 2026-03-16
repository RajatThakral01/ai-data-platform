import json
import os
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import HTTPException

MAX_SESSIONS = 50
SESSION_EXPIRY_SECONDS = 2 * 60 * 60  # 2 hours

_sessions: Dict[str, Dict[str, Any]] = {}

_redis = None
_backend = "memory"

try:
    import redis  # type: ignore

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            _pool = redis.ConnectionPool.from_url(redis_url)
            _redis = redis.Redis(connection_pool=_pool)
            _redis.ping()
            _backend = "redis"
        except Exception:
            _redis = None
            _backend = "memory"
except Exception:
    _redis = None
    _backend = "memory"

if _backend == "redis":
    print("Session store: Redis connected (REDIS_URL)")
else:
    print("Session store: using in-memory fallback")


def get_backend() -> str:
    return _backend


def _redis_key(session_id: str) -> str:
    return f"session:{session_id}"


def _cleanup_expired_sessions() -> None:
    now = time.time()
    expired_ids = [
        session_id
        for session_id, data in _sessions.items()
        if now - data.get("created_at", 0) > SESSION_EXPIRY_SECONDS
    ]
    for session_id in expired_ids:
        del _sessions[session_id]


def create_session() -> str:
    """Create a new session and return the ID."""
    if _backend == "redis":
        session_id = str(uuid.uuid4())
        key = _redis_key(session_id)
        payload = {"created_at": json.dumps(time.time())}
        _redis.hset(key, mapping=payload)
        _redis.expire(key, SESSION_EXPIRY_SECONDS)
        return session_id

    _cleanup_expired_sessions()
    if len(_sessions) >= MAX_SESSIONS:
        raise HTTPException(status_code=429, detail="Maximum number of sessions reached")

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "created_at": time.time(),
    }
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session data by string ID."""
    if _backend == "redis":
        key = _redis_key(session_id)
        data = _redis.hgetall(key)
        if not data:
            return None
        result: Dict[str, Any] = {}
        for raw_key, raw_value in data.items():
            key_str = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else str(raw_key)
            value_str = raw_value.decode("utf-8") if isinstance(raw_value, bytes) else str(raw_value)
            result[key_str] = json.loads(value_str)
        return result

    _cleanup_expired_sessions()
    return _sessions.get(session_id)


def update_session(session_id: str, key: str, value: Any) -> None:
    """Update a specific key in the session dictionary."""
    if _backend == "redis":
        redis_key = _redis_key(session_id)
        _redis.hset(redis_key, key, json.dumps(value))
        _redis.expire(redis_key, SESSION_EXPIRY_SECONDS)
        return

    if session_id in _sessions:
        _sessions[session_id][key] = value


def delete_session(session_id: str) -> None:
    if _backend == "redis":
        _redis.delete(_redis_key(session_id))
        return

    _sessions.pop(session_id, None)
