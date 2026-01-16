import os
from supabase import create_client, Client

_SUPABASE: Client | None = None


def get_supabase() -> Client:
    """
    Lazily initialize Supabase client.
    Prevents app from crashing at import time if env vars are missing.
    """
    global _SUPABASE

    if _SUPABASE is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise RuntimeError(
                "SUPABASE_URL or SUPABASE_KEY environment variables are missing"
            )

        _SUPABASE = create_client(supabase_url, supabase_key)

    return _SUPABASE
