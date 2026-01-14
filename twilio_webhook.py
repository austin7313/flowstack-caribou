from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from supabase_client import supabase
from datetime import datetime
import time

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    ProfileName: str = Form(None)
):
    customer_phone = From.replace("whatsapp:", "").replace("+", "")
    customer_name = ProfileName or "Unknown"
    message = Body.strip()

    print(f"📩 WhatsApp from {customer_phone}: {message}")

    try:
        supabase.table("orders").insert({
            "id": f"MSG-{int(time.time() * 1000)}",
            "customer_phone": customer_phone,
            "customer_name": customer_name,
            "items": "N/A",
            "amount": 0,
            "status": "received",
            "order_status": "none",
            "raw_message": message,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print("❌ Supabase error:", e)

    response = MessagingResponse()
    response.message("✅ FlowStack received your message. Reply MENU to continue.")

    return str(response)
