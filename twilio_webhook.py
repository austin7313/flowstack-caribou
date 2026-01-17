from fastapi import APIRouter, Request, Response
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime

from utils import normalize_text, generate_id
from session_logic import get_or_create_session, update_session
from supabase_client import get_supabase

router = APIRouter()

MENU = """🍽 CARIBOU KARIBU
Burger – 500
Fries – 200

Reply:
ORDER → to place order
"""

def parse_order(text: str):
    items = []
    amount = 0

    if "burger" in text:
        items.append("Burger")
        amount += 500
    if "fries" in text:
        items.append("Fries")
        amount += 200

    if not items:
        return None

    return {"items": " + ".join(items), "amount": amount}


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        form = await request.form()
        body = normalize_text(form.get("Body", ""))
        phone = form.get("From", "").replace("whatsapp:", "").replace("+", "")

        session = get_or_create_session(phone)
        resp = MessagingResponse()

        # GREETING
        if body in ["hi", "hello", "hey"]:
            resp.message("👋 Welcome to ChatPESA\n\nReply MENU to continue.")
            return Response(str(resp), media_type="application/xml")

        # MENU
        if body == "menu":
            resp.message(MENU)
            return Response(str(resp), media_type="application/xml")

        # ORDER INTENT
        if body == "order":
            update_session(phone, state="ordering")
            resp.message("📝 What would you like?\nExample:\nBurger + Fries")
            return Response(str(resp), media_type="application/xml")

        # ORDER PARSE
        if session["state"] == "ordering":
            order = parse_order(body)
            if not order:
                resp.message("❌ Invalid order. Try again.")
                return Response(str(resp), media_type="application/xml")

            order_id = generate_id("ORD")

            get_supabase().table("orders").insert({
                "id": order_id,
                "phone": phone,
                "items": order["items"],
                "amount": order["amount"],
                "status": "awaiting_payment",
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            update_session(phone, state="awaiting_payment", order_id=order_id)

            resp.message(
                f"""✅ Order received

📋 {order['items']}
💰 KES {order['amount']}

Reply PAY to complete payment."""
            )
            return Response(str(resp), media_type="application/xml")

        # PAYMENT TRIGGER (MPESA NEXT)
        if body == "pay" and session["state"] == "awaiting_payment":
            resp.message("📲 Payment request coming shortly…")
            return Response(str(resp), media_type="application/xml")

        # FALLBACK
        resp.message("❓ Reply MENU to continue.")
        return Response(str(resp), media_type="application/xml")

    except Exception as e:
        # CRITICAL: always return 200 to Twilio
        resp = MessagingResponse()
        resp.message("⚠️ Temporary issue. Try again.")
        return Response(str(resp), media_type="application/xml")
