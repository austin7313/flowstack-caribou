import os
from fastapi import APIRouter, Form, HTTPException
from twilio.twiml.messaging_response import MessagingResponse
from supabase_client import supabase
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Restaurant config
RESTAURANT = {
    "name": "CARIBOU KARIBU",
    "paybill": "247247",
    "owner_phone": "0722275271"
}

def generate_order_id():
    """Generate unique order ID"""
    import random
    return f"ORD{random.randint(100000, 999999)}"

def parse_order_message(message: str):
    """Extract order details from customer message"""
    # Simple parser - you can make this smarter later
    message_lower = message.lower()
    
    # Detect menu items
    items = []
    amount = 0
    
    if "butter chicken" in message_lower or "butter" in message_lower:
        items.append("Butter Chicken")
        amount += 850
    
    if "beef" in message_lower:
        items.append("Beef Curry")
        amount += 800
    
    if "naan" in message_lower:
        items.append("Naan Bread")
        amount += 150
    
    if "rice" in message_lower:
        items.append("Rice")
        amount += 100
    
    # Default if no match
    if not items:
        items.append("Custom Order")
        amount = 1000
    
    return {
        "items": " + ".join(items),
        "amount": amount
    }

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...),
    ProfileName: str = Form(None)
):
    """
    Receives WhatsApp messages from Twilio
    Processes orders and sends payment requests
    """
    try:
        # Clean phone number
        customer_phone = From.replace("whatsapp:", "").replace("+", "")
        customer_name = ProfileName or "Customer"
        message_body = Body.strip()
        
        print(f"📱 Message from {customer_name} ({customer_phone}): {message_body}")
        
        # Parse order
        order_details = parse_order_message(message_body)
        order_id = generate_order_id()
        
        # Save to Supabase
        order_data = {
            "id": order_id,
            "customer_phone": customer_phone,
            "customer_name": customer_name,
            "items": order_details["items"],
            "amount": order_details["amount"],
            "status": "awaiting_payment",
            "order_status": "new",
            "payment_code": order_id,
            "raw_message": message_body,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("orders").insert(order_data).execute()
        print(f"✅ Order saved to Supabase: {order_id}")
        
        # Send payment request to customer
        response = MessagingResponse()
        payment_message = f"""✅ Order received from {RESTAURANT['name']}!

📋 Your Order:
{order_details['items']}

💰 Total: KES {order_details['amount']:,}

💳 Pay Now:
Paybill: {RESTAURANT['paybill']}
Account: {order_id}

Reply DONE when paid.
Order ID: {order_id}"""
        
        response.message(payment_message)
        
        print(f"📤 Payment request sent to {customer_phone}")
        
        return str(response)
        
    except Exception as e:
        print(f"❌ Error processing webhook: {str(e)}")
        
        # Send error message to customer
        response = MessagingResponse()
        response.message(f"Sorry, there was an error processing your order. Please try again or call us directly.")
        
        return str(response)

@router.post("/payment-callback")
async def mpesa_callback(request: dict):
    """
    Receives M-Pesa payment callbacks from Daraja API
    Updates order status when payment confirmed
    """
    try:
        # TODO: Implement M-Pesa callback logic
        # For now, this is a placeholder
        
        print("💰 M-Pesa callback received")
        print(request)
        
        return {"status": "callback received"}
        
    except Exception as e:
        print(f"❌ Error processing M-Pesa callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
