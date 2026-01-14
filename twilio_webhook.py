import os
from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from supabase_client import supabase
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    ProfileName: str = Form(None)
):
    """
    Receives WhatsApp messages from Twilio
    Logs them to Supabase
    Sends a generic acknowledgment
    """
    try:
        # Clean phone number
        customer_phone = From.replace("whatsapp:", "").replace("+", "")
        customer_name = ProfileName or "Customer"
        message_body = Body.strip()
        
        print(f"📱 Message from {customer_name} ({customer_phone}): {message_body}")
        
        # Save to Supabase
        log_data = {
            "id": f"MSG{int(datetime.utcnow().timestamp() * 1000)}",  # unique ID
            "customer_phone": customer_phone,
            "customer_name": customer_name,
            "items": "N/A",  # placeholder
            "amount": 0,      # placeholder
            "status": "received",
            "order_status": "N/A",
            "payment_code": None,
            "raw_message": message_body,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("orders").insert(log_data).execute()
        print(f"✅ Message logged in Supabase")
        
        # Respond to customer
        response = MessagingResponse()
        response.message("✅ Message received! Our team will respond shortly.")
        
        return str(response)
    
    except Exception as e:
        print(f"❌ Error processing webhook: {str(e)}")
        response = MessagingResponse()
        response.message("❌ Error logging your message. Please try again later.")
        return str(response)
