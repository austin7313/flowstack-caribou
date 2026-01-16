from fastapi import APIRouter, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import random

from supabase_client import get_supabase

router = APIRouter()

RESTAURANT = {
    "name": "CARIBOU KARIBU",
    "paybill": "247247"
}

MENU_TEXT = """🍽 MENU – CARIBOU KARIBU
Burger – 500
Fries – 200

Reply ORDER to proceed.
"""


def generate_order_id():
    return f"ORD{random.randint(100000, 999999)}"


def twilio_xml(msg: str):
    r = MessagingResponse()
    r.message(msg)
    return Response(content=str(r), media_type="application/xml")


def parse_food(msg: str):
    items = []
    amount = 0

    if "burger" in msg:
        items.append("Burger")
        amount += 500
    if "fries" in msg:
        items.append("Fries")
        amount += 200

    if not items:
        return None

    return {
        "items": " + ".join(items),
        "amount": amount
    }


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    message = form.get("Body", "").strip().lower()
    from_number = form.get("From", "").replace("whatsapp:", "").replace("+", "")

    # 1️⃣ GREETINGS (NO DATABASE)
    if message in ["hi", "hello", "hey"]:
        return twilio_xml(
            "👋 Welcome to CARIBOU KARIBU!\n\nReply MENU to see options."
        )

    # 2️⃣ MENU (NO DATABASE)
    if message == "menu":
        return twilio_xml(MENU_TEXT)

    # 3️⃣ ORDER INTENT (NO DATABASE)
    if message == "order":
        return twilio_xml(
            "📝 What would you like to order?\n\nExample:\nBurger\nFries\nBurger + Fries"
        )

    # 4️⃣ FOOD MESSAGE (DATABASE REQUIRED)
    order = parse_food(message)
    if order:
        try:
            supabase = get_supabase()
            order_id = generate_order_id()

            supabase.table("orders").insert({
                "id": order_id,
                "customer_phone": from_number,
                "items": order["items"],
                "amount": order["amount"],
                "status": "awaiting_payment",
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            return twilio_xml(
                f"""✅ Order received!

📋 {order['items']}
💰 Total: KES {order['amount']}

💳 Paybill: {RESTAURANT['paybill']}
📌 Account: {order_id}

Reply DONE after payment."""
            )

        except Exception as e:
            # 🔥 NEVER CRASH TWILIO
            return twilio_xml(
                "⚠️ Sorry, we’re having a system issue. Please try again in a moment."
            )

    # 5️⃣ FALLBACK
    return twilio_xml(
        "❓ I didn’t understand that.\n\nReply MENU to see options."
    )
