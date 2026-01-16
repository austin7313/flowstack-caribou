import requests
import base64
from datetime import datetime
from supabase_client import get_supabase

# 👇 Replace these with your actual M-Pesa sandbox/production credentials
MPESA_SHORTCODE = "4031193"
MPESA_PASSKEY = "5a64ad290753ed331b662cf6d83d3149367867c102f964f522390ccbd85cb282"
MPESA_CONSUMER_KEY = "B05zln19QXC3OBL6YuCkdhZ8zvYqZtXP"
MPESA_CONSUMER_SECRET = "MYRasd2p9gGFcuCR"
MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"  # change to production when live
CALLBACK_URL = "https://flowstack-caribou-1.onrender.com/webhook/mpesa_callback"

def get_access_token():
    url = f"{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    response.raise_for_status()
    return response.json()["access_token"]

def stk_push(phone_number, amount, order_id):
    token = get_access_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}".encode()).decode()

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": order_id,
        "TransactionDesc": f"Payment for order {order_id}"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    resp = requests.post(f"{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

def handle_callback(callback_json):
    supabase = get_supabase()
    result = callback_json.get("Body", {}).get("stkCallback", {})
    order_id = result.get("CallbackMetadata", {}).get("Item", [{}])[0].get("Value")
    result_code = result.get("ResultCode")
    
    if not order_id:
        return False

    if result_code == 0:  # success
        supabase.table("orders").update({
            "status": "completed",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", order_id).execute()
    else:  # failed
        supabase.table("orders").update({
            "status": "failed",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", order_id).execute()

    return True
