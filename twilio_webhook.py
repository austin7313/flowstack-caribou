from fastapi import APIRouter, Form, Request
from twilio.twiml.messaging_response import MessagingResponse
from supabase_client import supabase
from datetime import datetime
import random, os, base64, requests
from requests.auth import HTTPBasicAuth

router = APIRouter()

# Restaurant config
RESTAURANT = {
    "name": "CARIBOU KARIBU",
    "paybill": os.environ.get("DARAJA_SHORTCODE")  # Just for display
}

MENU_TEXT = """🍽 MENU – CARIBOU KARIBU
Burger – 500
Fries – 200

Reply ORDER to proceed.
"""

# M-Pesa credentials
SHORTCODE = os.environ.get("DARAJA_SHORTCODE")
PASSKEY = os.environ.get("DARAJA_PASSKEY")
CONSUMER_KEY = os.environ.get("DARAJA_CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("DARAJA_CONSUMER_SECRET")

if not all([SHORTCODE, PASSKEY, CONSUMER_KEY, CONSUMER_SECRET]):
    raise RuntimeError("Missing M-Pesa environment variables")

# ---------------- UTILITY FUNCTIONS ---------------- #

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

    return {"items": " + ".join(items), "amount": amount}

# ---------------- M-PESA FUNCTIONS ---------------- #

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET))
    response.raise_for_status()
    return response.json()["access_token"]

def initiate_payment(phone, amount, order_id):
    token = get_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://flowstack-caribou-1.onrender.com/webhook/payment-callback",
        "AccountReference": order_id,
        "TransactionDesc": f"Payment for {order_id}"
    }

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers=headers
    )
    return response.json()

# ---------------- WHATSAPP WEBHOOK ---------------- #

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    message = Body.strip().lower()
    customer_phone = From.replace("whatsapp:", "").replace("+", "")

    response = MessagingResponse()

    # 1️⃣ GREETING
    if is_greeting(message):
        response.message(
            "👋 Welcome to FlowStack!\n\nReply MENU to see options."
        )
        return str(response)

    # 2️⃣ MENU
    if is_menu(message):
        response.message(MENU_TEXT)
        return str(response)

    # 3️⃣ ORDER INTENT
    if is_order(message):
        response.message(
            "📝 What would you like to order?\n\nReply with items e.g:\nBurger\nFries\nBurger + Fries"
        )
        return str(response)

    # 4️⃣ FOOD MESSAGE
    order = parse_food(message)
    if order:
        order_id = generate_order_id()

        # Save order to Supabase
        supabase.table("orders").insert({
            "id": order_id,
            "customer_phone": customer_phone,
            "items": order["items"],
            "amount": order["amount"],
            "status": "awaiting_payment",
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # Trigger STK Push
        try:
            stk_response = initiate_payment(phone=customer_phone, amount=order["amount"], order_id=order_id)
            print(f"💰 STK Push Response: {stk_response}")
        except Exception as e:
            print(f"❌ Error initiating payment: {e}")

        response.message(
            f"""✅ Order received!

📋 {order['items']}
💰 Total: KES {order['amount']}

💳 Paybill: {RESTAURANT['paybill']}
📌 Account: {order_id}

You should receive an M-Pesa prompt shortly. Reply DONE after payment."""
        )
        return str(response)

    # 5️⃣ FALLBACK
    response.message(
        "❓ I didn’t understand that.\n\nReply MENU to see options."
    )
    return str(response)

# ---------------- M-PESA CALLBACK ---------------- #

@router.post("/payment-callback")
async def mpesa_callback(request: Request):
    data = await request.json()
    print("💰 M-Pesa callback received:", data)

    # Extract order ID and payment result
    # Daraja response JSON will vary; adjust as needed
    try:
        order_id = data["Body"]["stkCallback"]["CheckoutRequestID"]
        result_code = data["Body"]["stkCallback"]["ResultCode"]

        if result_code == 0:
            # Payment successful
            supabase.table("orders").update({
                "status": "paid",
                "paid_at": datetime.utcnow().isoformat()
            }).eq("id", order_id).execute()
            print(f"✅ Payment confirmed for order {order_id}")
        else:
            print(f"❌ Payment failed for order {order_id}, ResultCode: {result_code}")
    except Exception as e:
        print(f"❌ Error processing callback: {e}")

    return {"status": "received"}
