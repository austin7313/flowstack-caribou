from datetime import datetime
from supabase_client import get_supabase

def get_session(phone: str):
    supabase = get_supabase()

    res = supabase.table("sessions") \
        .select("*") \
        .eq("phone", phone) \
        .single() \
        .execute()

    if res.data:
        return res.data

    session = {
        "phone": phone,
        "state": "new",
        "last_message": None,
        "updated_at": datetime.utcnow().isoformat()
    }

    supabase.table("sessions").insert(session).execute()
    return session


def update_session(phone: str, state: str, last_message: str = None):
    supabase = get_supabase()

    supabase.table("sessions") \
        .update({
            "state": state,
            "last_message": last_message,
            "updated_at": datetime.utcnow().isoformat()
        }) \
        .eq("phone", phone) \
        .execute()
