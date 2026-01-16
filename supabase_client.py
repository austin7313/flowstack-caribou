import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Debug output
print(f"🔍 Supabase Environment Check:")
print(f"   URL: {SUPABASE_URL}")
print(f"   KEY length: {len(SUPABASE_KEY) if SUPABASE_KEY else 0}")
print(f"   KEY starts with: {SUPABASE_KEY[:20] if SUPABASE_KEY else 'NONE'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_KEY in environment variables")

def get_supabase() -> Client:
    """
    Returns a Supabase client instance
    Creates a new client on each call to avoid stale connections
    """
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client created successfully")
        return client
    except Exception as e:
        print(f"❌ Failed to create Supabase client: {str(e)}")
        raise

# Also export a singleton instance for simpler imports
supabase: Client = get_supabase()

print("✅ Supabase client initialized")
