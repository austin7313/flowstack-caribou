from fastapi import APIRouter, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import random

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

def is_greeting(msg: str):
    return msg in ["hi", "hello", "hey"]

def is_menu(msg: str):
    return msg == "menu"

def is_order(msg: str):
    return msg == "order"

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
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
):
    message = Body.strip().lower()
    customer_phone = From.replace("whatsapp:", "").replace("+", "")

    response = MessagingResponse()

    # 1️⃣ GREETING
    if is_greeting(message):
        response.message(
            "👋 Welcome to FlowStack!\n\nReply MENU to see options."
        )
        return Response(content=str(response), media_type="application/xml")

    # 2️⃣ MENU
    if is_menu(message):
        response.message(MENU_TEXT)
        return Response(content=str(response), media_type="application/xml")

    # 3️⃣ ORDER INTENT
    if is_order(message):
        response.message(
            "📝 What would you like to order?\n\nReply with items e.g:\nBurger\nFries\nBurger + Fries"
        )
        return Response(content=str(response), media_type="application/xml")

    # 4️⃣ FOOD MESSAGE
    order = parse_food(message)
    if order:
        order_id = generate_order_id()

        # Here you can add database insert later if ready
        # For now, just send response

        response.message(
            f"""✅ Order received!

📋 {order['items']}
💰 Total: KES {order['amount']}

💳 Paybill: {RESTAURANT['paybill']}
📌 Account: {order_id}

Reply DONE after payment."""
        )
        return Response(content=str(response), media_type="application/xml")

    # 5️⃣ FALLBACK
    response.message(
        "❓ I didn’t understand that.\n\nReply MENU to see options."
    )
    return Response(content=str(response), media_type="application/xml")
