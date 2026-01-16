from datetime import datetime
import uuid

def get_or_create_session(supabase, business_id, phone):
    existing = (
        supabase.table("sessions")
        .select("*")
        .eq("business_id", business_id)
        .eq("user_phone", phone)
        .single()
        .execute()
    )

    if existing.data:
        return existing.data

    session = {
        "id": str(uuid.uuid4()),
        "business_id": business_id,
        "user_phone": phone,
        "state": "greeting",
        "flow": None,
        "context": {},
        "last_seen": datetime.utcnow().isoformat()
    }

    supabase.table("sessions").insert(session).execute()
    return session
