from fastapi import APIRouter, Request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import random
import json

from supabase_client import get_supabase
from mpesa_client import stk_push, handle_callback as mpesa_handle_callback

router = APIRouter()

# ------------------------------
# CONFIG
# ------------------------------
RESTAURANT = {
    "name": "CARIBOU KARIBU",
    "paybill": "247247"
}

MENU_ITEMS = {
    "burger": 500,
    "fries": 200
}

MENU_TEXT = "🍽 MENU – CARIBOU KARIBU\n"
for item, price in MENU_ITEMS.items():
    MENU_TEXT += f"{item.title()} – {price}\n"
MENU_TEXT += "\nReply ORDER to proceed."

GREETINGS = ["hi", "hello", "hey"]

# ------------------------------
# UTILITY FUNCTIONS
# ------------------------------
def generate_order_id():
    return f"ORD{random.randint(100000, 999999)}"

def parse_food(msg: str):
    items = []
    amount = 0
    for item, price in MENU_ITEMS.items():
        if item in msg:
            items.append(item.title())
            amount += price
    if not items:
        return None
    return {"items": " + ".join(items), "amount": amount}

# ------------------------------
# SESSION MANAGEMENT
# ------------------------------
def get_or_create_session(supabase, phone):
    existing = supabase.table("sessions").select("*").eq("phone", phone).execute()
    if existing.data:
        return existing.data[0]
    new_session = supabase.table("sessions").insert({
        "phone": phone,
        "context": json.dumps({}),
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    return new_session.data[0]

def update_session_context(supabase, phone, context):
    supabase.table("sessions").update({"context": json.dumps(context)}).eq("phone", phone).execute()

# ------------------------------
# WHATSAPP WEBHOOK
# ------------------------------
@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    supabase = get_supabase()
    form = await request.form()
    message = form.get("Body", "").strip().lower()
    phone = form.get("From", "").replace("whatsapp:", "").replace("+", "")
    response = MessagingResponse()

    session = get_or_create_session(supabase, phone)
    context = json.loads(session["context"])

    # 1️⃣ GREETING
    if message in GREETINGS:
        response.message(f"👋 Welcome to {RESTAURANT['name']}!\nReply MENU to see options.")
        context["state"] = "greeted"
        update_session_context(supabase, phone, context)
        return str(response)

    # 2️⃣ MENU
    if message == "menu":
        response.message(MENU_TEXT)
        context["state"] = "menu_shown"
        update_session_context(supabase, phone, context)
        return str(response)

    # 3️⃣ ORDER INIT
    if message == "order":
        response.message("📝 What would you like to order? Example:\nBurger\nFries\nBurger + Fries")
        context["state"] = "awaiting_food"
        update_session_context(supabase, phone, context)
        return str(response)

    # 4️⃣ PROCESS FOOD MESSAGE
    if context.get("state") == "awaiting_food":
        order = parse_food(message)
        if order:
            order_id = generate_order_id()

            # Save order
            supabase.table("orders").insert({
                "id": order_id,
                "customer_phone": phone,
                "items": order["items"],
                "amount": order["amount"],
                "status": "awaiting_payment",
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            # Trigger M-Pesa STK push
            try:
                stk_push(phone, order["amount"], order_id)
                response.message(
                    f"✅ Order received!\n\n📋 {order['items']}\n💰 Total: KES {order['amount']}\n\n"
                    f"💳 Payment request sent to your phone.\nOrder ID: {order_id}\nReply DONE after payment."
                )
            except Exception as e:
                response.message(f"❌ Could not initiate payment. Try again later.\nError: {str(e)}")

            context["state"] = "awaiting_payment"
            context["last_order_id"] = order_id
            update_session_context(supabase, phone, context)
            return str(response)
        else:
            response.message("❌ Could not understand your order. Please reply with items like:\nBurger\nFries\nBurger + Fries")
            return str(response)

    # 5️⃣ PAYMENT CONFIRMATION
    if message == "done" and context.get("state") == "awaiting_payment":
        order_id = context.get("last_order_id")
        order = supabase.table("orders").select("*").eq("id", order_id).execute()
        if order.data and order.data[0]["status"] == "completed":
            response.message(f"✅ Payment confirmed! Your order {order_id} is being prepared.")
            context["state"] = "completed"
        else:
            response.message(f"⚠️ Payment not yet confirmed. Please complete payment for order {order_id}.")
        update_session_context(supabase, phone, context)
        return str(response)

    # 6️⃣ FALLBACK
    response.message("❓ I didn’t understand that. Reply MENU to see options.")
    return str(response)

# ------------------------------
# M-PESA CALLBACK
# ------------------------------
@router.post("/mpesa_callback")
async def mpesa_callback(request: Request):
    data = await request.json()
    success = mpesa_handle_callback(data)
    return {"success": success}
