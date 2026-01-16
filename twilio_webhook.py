from fastapi import APIRouter, Request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import random
import json

from supabase_client import get_supabase
from mpesa_client import stk_push

router = APIRouter()

# 🏷 Restaurant / Business Info
RESTAURANT = {
    "name": "CARIBOU KARIBU",
    "paybill": "247247"
}

MENU_TEXT = """🍽 MENU – CARIBOU KARIBU
Burger – 500
Fries – 200

Reply ORDER to proceed.
"""

# ------------------------------
# UTILITY FUNCTIONS
# ------------------------------
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

# ------------------------------
# WHATSAPP WEBHOOK
# ------------------------------
@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    supabase = get_supabase()
    form = await request.form()
    message = form.get("Body", "").strip().lower()
    from_number = form.get("From", "").replace("whatsapp:", "").replace("+", "")
    response = MessagingResponse()

    # 1️⃣ GREETING
    if is_greeting(message):
        response.message(
            f"👋 Welcome to {RESTAURANT['name']}!\n\nReply MENU to see options."
        )
        return str(response)

    # 2️⃣ MENU
    if is_menu(message):
        response.message(MENU_TEXT)
        return str(response)

    # 3️⃣ ORDER INTENT
    if is_order(message):
        response.message(
            "📝 What would you like to order?\n\nExample:\nBurger\nFries\nBurger + Fries"
        )
        return str(response)

    # 4️⃣ FOOD MESSAGE
    order = parse_food(message)
    if order:
        order_id = generate_order_id()

        # Save order to Supabase
        supabase.table("orders").insert({
            "id": order_id,
            "customer_phone": from_number,
            "items": order["items"],
            "amount": order["amount"],
            "status": "awaiting_payment",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # Trigger M-Pesa STK Push
        try:
            stk_response = stk_push(from_number, order["amount"], order_id)
            response.message(
                f"""✅ Order received!

📋 {order['items']}
💰 Total: KES {order['amount']}

💳 Payment request sent to your phone. Complete the payment to finalize your order.

Order ID: {order_id}
"""
            )
        except Exception as e:
            response.message(
                f"❌ Could not initiate payment. Try again later.\nError: {str(e)}"
            )
        return str(response)

    # 5️⃣ FALLBACK
    response.message(
        "❓ I didn’t understand that.\n\nReply MENU to see options."
    )
    return str(response)


# ------------------------------
# MPESA CALLBACK
# ------------------------------
@router.post("/mpesa_callback")
async def mpesa_callback(request: Request):
    data = await request.json()
    from mpesa_client import handle_callback

    success = handle_callback(data)
    return {"success": success}


# ------------------------------
# SESSION MANAGEMENT (Optional)
# ------------------------------
@router.post("/session_test")
async def session_test(request: Request):
    """
    Example endpoint to check session memory in Supabase 'sessions' table
    """
    supabase = get_supabase()
    form = await request.form()
    phone = form.get("From", "").replace("whatsapp:", "").replace("+", "")

    # Load existing session or create new
    existing = supabase.table("sessions").select("*").eq("phone", phone).execute()
    if existing.data:
        session = existing.data[0]
        return {"session": session}
    else:
        new_session = supabase.table("sessions").insert({
            "phone": phone,
            "created_at": datetime.utcnow().isoformat(),
            "context": {}
        }).execute()
        return {"session": new_session.data[0]}
