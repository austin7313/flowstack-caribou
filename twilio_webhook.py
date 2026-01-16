from fastapi import APIRouter, Request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime

from supabase_client import get_supabase
from session_manager import get_or_create_session
from flow_engine import route_message

router = APIRouter()

BUSINESS_ID = "caribou-karibu-uuid"  # later dynamic

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    supabase = get_supabase()
    form = await request.form()

    message = form.get("Body", "").strip().lower()
    phone = form.get("From", "").replace("whatsapp:", "").replace("+", "")

    session = get_or_create_session(supabase, BUSINESS_ID, phone)

    action = route_message(message, session)

    response = MessagingResponse()

    if action == "menu":
        response.message("👋 Welcome to CHATPESA\nReply MENU to begin.")
        session["state"] = "menu"

    elif action == "show_menu":
        response.message("🍔 Burger 500\n🍟 Fries 200\nReply ORDER to proceed.")
        session["state"] = "menu"

    elif action == "ordering":
        response.message("📝 What would you like to order?")
        session["state"] = "ordering"

    else:
        response.message("❓ I didn’t understand. Reply MENU.")

    supabase.table("sessions").update({
        "state": session["state"],
        "last_seen": datetime.utcnow().isoformat()
    }).eq("id", session["id"]).execute()

    return str(response)
