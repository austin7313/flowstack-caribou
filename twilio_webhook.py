from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
from supabase_rest import insert_order
import random

router = APIRouter()

MENU = """🍽 MENU
Burger – 500
Fries – 200

Reply ORDER to proceed.
"""

def gen_order_id():
    return f"ORD{random.randint(100000,999999)}"

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    msg = Body.strip().lower()
    resp = MessagingResponse()

    # greetings
    if msg in ["hi", "hello", "hey"]:
        resp.message("👋 Welcome to FlowStack!\nReply MENU to see options.")
        return str(resp)

    if msg == "menu":
        resp.message(MENU)
        return str(resp)

    if msg == "order":
        order_id = gen_order_id()

        order = {
            "id": order_id,
            "customer_phone": From.replace("whatsapp:", ""),
            "items": "Burger",
            "amount": 500,
            "status": "awaiting_payment",
            "created_at": datetime.utcnow().isoformat()
        }

        await insert_order(order)

        resp.message(
            f"""✅ Order received!

💰 Pay KES 500
Paybill: 247247
Account: {order_id}

Reply DONE after payment."""
        )
        return str(resp)

    resp.message("❓ Unknown command. Reply MENU.")
    return str(resp)
