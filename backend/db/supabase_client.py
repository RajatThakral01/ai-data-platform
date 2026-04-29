import os
from supabase import create_client, Client

_client: Client | None = None

def get_supabase() -> Client | None:
    global _client
    if _client is not None:
        return _client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Supabase: SUPABASE_URL or SUPABASE_KEY not set — Supabase disabled")
        return None
    try:
        _client = create_client(url, key)
        print(f"Supabase: connected to {url}")
        return _client
    except Exception as e:
        print(f"Supabase: connection failed — {e}")
        return None