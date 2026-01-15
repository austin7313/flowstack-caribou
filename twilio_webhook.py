import os
from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from supabase_client import supabase
from datetime import datetime
import random

router = APIRouter()

# -------- CONFIG --------
RESTAURANT = {
    "name": "CARIBOU KARIBU",
    "paybill": "247247"
}

ENTRY_WORDS = ["hi", "hello", "hey", "start", "menu"]
ORDER_WORDS = ["order"]

MENU_TEXT = """🍽 MENU
Burger – 500
Fries – 200

Reply ORDER to proceed."""

# -------- HELPERS --------
def generate_order_id():
    return f"ORD{random.randint(100000, 999999)}"

def normalize(text: str):
    return text.lower().strip()

def parse_items(message: str):
    items = []
    amount = 0
    msg = message.lower()

    if "burger" in msg:
        items.append("Burger")
        amount += 500

    if "fries" in msg:
        items.append("Fries")
        amount += 200

    return items, amount

# -------- WEBHOOK --------
@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    msg = normalize(Body)
    phone = From.replace("whatsapp:", "").replace("+", "")

    response = MessagingResponse()

    # 1️⃣ ENTRY POINT (hi / hello / menu)
    if msg in ENTRY_WORDS:
        response.message(f"👋 Welcome to {RESTAURANT['name']}!\n\n{MENU_TEXT}")
        return str(response)

    # 2️⃣ ORDER INTENT
    if msg in ORDER_WORDS:
        response.message("📝 What would you like to order?\nExample: burger and fries")
        return str(response)

    # 3️⃣ FOOD SELECTION
    items, amount = parse_items(msg)

    if items:
        order_id = generate_order_id()

        supabase.table("orders").insert({
            "id": order_id,
            "customer_phone": phone,
            "items": " + ".join(items),
            "amount": amount,
            "status": "awaiting_payment",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        response.message(
            f"""✅ Order Received!

📦 Items: {' + '.join(items)}
💰 Total: KES {amount}

💳 Pay via M-Pesa:
Paybill: {RESTAURANT['paybill']}
Account: {order_id}

Reply DONE after payment."""
        )
        return str(response)

    # 4️⃣ FALLBACK (VERY RARE)
    response.message("❓ I didn’t understand that.\nType MENU to start.")
    return str(response)
