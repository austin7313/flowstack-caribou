from datetime import datetime
from supabase_client import get_supabase

def get_or_create_session(phone: str):
    supabase = get_supabase()

    session = (
        supabase
        .table("sessions")
        .select("*")
        .eq("phone", phone)
        .eq("active", True)
        .limit(1)
        .execute()
    )

    if session.data:
        return session.data[0]

    new_session = {
        "phone": phone,
        "state": "new",
        "active": True,
        "created_at": datetime.utcnow().isoformat()
    }

    supabase.table("sessions").insert(new_session).execute()
    return new_session


def update_session(phone: str, **updates):
    supabase = get_supabase()
    supabase.table("sessions").update(updates).eq("phone", phone).eq("active", True).execute()
