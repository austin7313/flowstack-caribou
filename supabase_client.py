from supabase import create_client
from settings import settings

_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    return _supabase
