import os
import requests
import logging

logger = logging.getLogger(__name__)

METABASE_URL = os.getenv("METABASE_SITE_URL", "http://ai_platform_metabase:3001")
METABASE_EMAIL = os.getenv("METABASE_EMAIL", "")
METABASE_PASSWORD = os.getenv("METABASE_PASSWORD", "")

_token = None

def get_token() -> str | None:
    global _token
    if _token:
        return _token
    try:
        resp = requests.post(
            f"{METABASE_URL}/api/session",
            json={"username": METABASE_EMAIL, "password": METABASE_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            _token = resp.json()["id"]
            return _token
    except Exception as e:
        logger.error(f"Metabase auth failed: {e}")
    return None

def metabase_get(path: str) -> dict | None:
    token = get_token()
    if not token:
        return None
    try:
        resp = requests.get(
            f"{METABASE_URL}{path}",
            headers={"X-Metabase-Session": token},
            timeout=10
        )
        return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        logger.error(f"Metabase GET {path} failed: {e}")
        return None

def metabase_post(path: str, data: dict) -> dict | None:
    token = get_token()
    if not token:
        return None
    try:
        resp = requests.post(
            f"{METABASE_URL}{path}",
            headers={"X-Metabase-Session": token},
            json=data,
            timeout=15
        )
        return resp.json() if resp.status_code in [200, 202] else None
    except Exception as e:
        logger.error(f"Metabase POST {path} failed: {e}")
        return None

def get_database_id() -> int | None:
    dbs = metabase_get("/api/database")
    if not dbs:
        return None
    for db in dbs.get("data", []):
        if "AI Data Platform" in db.get("name", "") or "supabase" in db.get("details", {}).get("host", "").lower():
            return db["id"]
    return None

def get_table_id(database_id: int, table_name: str) -> int | None:
    tables = metabase_get(f"/api/database/{database_id}/metadata")
    if not tables:
        return None
    for table in tables.get("tables", []):
        if table.get("name", "").lower() == table_name.lower():
            return table["id"]
    return None
