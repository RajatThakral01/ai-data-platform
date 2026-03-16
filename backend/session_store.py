import uuid
import time
from typing import Dict, Any

# In-memory dictionary: {session_id: {"df": DataFrame, "filename": str, ...}}
_SESSIONS: Dict[str, Dict[str, Any]] = {}

MAX_SESSIONS = 50
SESSION_EXPIRY_SECONDS = 2 * 60 * 60  # 2 hours

def create_session() -> str:
    """Create a new session and return the ID, optionally evicting old ones."""
    _cleanup_old_sessions()
    
    session_id = str(uuid.uuid4())
    _SESSIONS[session_id] = {
        "created_at": time.time(),
        "last_accessed": time.time()
    }
    return session_id

def get_session(session_id: str) -> Dict[str, Any]:
    """Retrieve session data by string ID."""
    sess = _SESSIONS.get(session_id)
    if sess:
        sess["last_accessed"] = time.time()
    return sess

def update_session(session_id: str, key: str, value: Any) -> None:
    """Update a specific key in the session dictionary."""
    if session_id in _SESSIONS:
        _SESSIONS[session_id][key] = value
        _SESSIONS[session_id]["last_accessed"] = time.time()

def _cleanup_old_sessions() -> None:
    """Remove sessions older than 2 hours or if over limit (FIFO)."""
    current_time = time.time()
    expired = [
        sid for sid, data in _SESSIONS.items() 
        if current_time - data.get("last_accessed", 0) > SESSION_EXPIRY_SECONDS
    ]
    for sid in expired:
        del _SESSIONS[sid]
        
    if len(_SESSIONS) >= MAX_SESSIONS:
        # Find oldest remaining
        oldest = min(_SESSIONS.items(), key=lambda x: x[1].get("last_accessed", 0))
        del _SESSIONS[oldest[0]]
