from fastapi import APIRouter, Request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import random
import json
import requests

from supabase_client import get_supabase

router = APIRouter()


# Utility functions
def generate_order_id():
    return f"ORD{random.randint(100000, 999999)}"


async def get_or_create_session(supabase, phone: str):
    resp = supabase.table("sessions").select("*").eq("phone", phone).execute()
    session = resp.data[0] if resp.data else None

    if not session:
        session_data = {
            "phone": phone,
            "context": json.dumps({"state": "new", "business_id": None, "last_order": None}),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        supabase.table("sessions").insert(session_data).execute()
        session = session_data

    return session


async def update_session(supabase, phone: str, context: dict):
    supabase.table("sessions").update({
        "context": json.dumps(context),
        "updated_at": datetime.utcnow().isoformat()
    }).eq("phone", phone).execute()


async def get_business(supabase, business_id: str = None):
    if business_id:
        resp = supabase.table("businesses").select("*").eq("id", business_id).execute()
        if resp.data:
            return resp.data[0]

    resp = supabase.table("businesses").select("*").limit(1).execute()
    return resp.data[0] if resp.data else None


def parse_food(msg: str, menu: dict):
    items = []
    amount = 0
    for key, price in menu.items():
        if key.lower() in msg:
            items.append(key)
            amount += price
    if not items:
        return None
    return {"items": " + ".join(items), "amount": amount}


def initiate_mpesa_payment(phone: str, amount: int, account_ref: str, short_code: str, passkey: str, consumer_key: str, consumer_secret: str):
    """
    Initiates an STK Push via Mpesa API
    """
    # 🔹 Get OAuth token
    oauth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(oauth_url, auth=(consumer_key, consumer_secret))
    token = r.json().get("access_token")

    # 🔹 Prepare STK push payload
    stk_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    payload = {
        "BusinessShortCode": short_code,
        "Password": passkey,  # Normally base64 of Shortcode+Passkey+Timestamp
        "Timestamp": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": short_code,
        "PhoneNumber": phone,
        "CallBackURL": "https://your-callback-url.com/payment",  # replace with actual endpoint
        "AccountReference": account_ref,
        "TransactionDesc": "Order Payment"
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(stk_url, json=payload, headers=headers)
    return r.json()


# Main webhook
@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    supabase = get_supabase()

    form = await request.form()
    message = form.get("Body", "").strip().lower()
    from_number = form.get("From", "").replace("whatsapp:", "").replace("+", "")

    response = MessagingResponse()

    # Load session & business
    session = await get_or_create_session(supabase, from_number)
    context = json.loads(session["context"])
    business = await get_business(supabase, context.get("business_id"))
    menu = business.get("menu", {}) if business else {}
    menu_text = f"🍽 MENU – {business['name']}\n" if business else "🍽 MENU\n"
    for item, price in menu.items():
        menu_text += f"{item} – {price}\n"
    menu_text += "\nReply ORDER to proceed."

    # State machine
    state = context.get("state", "new")

    if state in ["new", "greeted"] and message in ["hi", "hello", "hey"]:
        context.update({"state": "greeted", "business_id": business["id"]})
        await update_session(supabase, from_number, context)
        response.message(f"👋 Welcome to {business['name']}!\n\nReply MENU to see options.")
        return str(response)

    if message == "menu":
        context.update({"state": "menu_viewed"})
        await update_session(supabase, from_number, context)
        response.message(menu_text)
        return str(response)

    if message == "order":
        context.update({"state": "awaiting_food"})
        await update_session(supabase, from_number, context)
        response.message("📝 What would you like to order?\nExample:\nBurger\nFries\nBurger + Fries")
        return str(response)

    if state == "awaiting_food":
        order = parse_food(message, menu)
        if order:
            order_id = generate_order_id()
            supabase.table("orders").insert({
                "id": order_id,
                "customer_phone": from_number,
                "business_id": business["id"],
                "items": order["items"],
                "amount": order["amount"],
                "status": "awaiting_payment",
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            # Initiate MPesa STK Push
            mpesa_response = initiate_mpesa_payment(
                phone=from_number,
                amount=order["amount"],
                account_ref=order_id,
                short_code=business["paybill"],
                passkey=business.get("mpesa_passkey"),
                consumer_key=business.get("mpesa_consumer_key"),
                consumer_secret=business.get("mpesa_consumer_secret")
            )

            context.update({"state": "awaiting_payment", "last_order": order_id})
            await update_session(supabase, from_number, context)

            response.message(
                f"""✅ Order received!

📋 {order['items']}
💰 Total: KES {order['amount']}

💳 Payment request sent via Mpesa. Check your phone to complete the payment.
📌 Account: {order_id}

Reply DONE after payment."""
            )
            return str(response)

    # Payment confirmation (user replies DONE)
    if message == "done" and state == "awaiting_payment":
        order_id = context.get("last_order")
        supabase.table("orders").update({"status": "paid", "paid_at": datetime.utcnow().isoformat()}).eq("id", order_id).execute()
        context.update({"state": "paid"})
        await update_session(supabase, from_number, context)
        response.message(f"🎉 Payment confirmed for order {order_id}. Thank you for ordering from {business['name']}!")
        return str(response)

    # Fallback
    response.message("❓ I didn’t understand that. Reply MENU to see options.")
    return str(response)
