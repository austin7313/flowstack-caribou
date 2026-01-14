from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from database import SessionLocal
from models import Order

router = APIRouter()

MENU = """
🍽 MENU
Burger – 500
Fries – 200

Reply ORDER to proceed.
"""

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    db = SessionLocal()

    try:
        # Normalize incoming WhatsApp number
        phone = From.replace("whatsapp:", "")

        response = MessagingResponse()

        text = Body.strip().lower()

        if text == "menu":
            response.message(MENU)
        elif text == "order":
            # For testing, just create a dummy order
            order = Order(customer_phone=phone, items="Burger + Fries", amount=700)
            db.add(order)
            db.commit()
            response.message("✅ Order received!\nReply PAY to receive M-Pesa prompt.")
        elif text == "pay":
            response.message("💰 M-Pesa payment prompt coming soon.")
        elif text == "help":
            response.message("📌 Commands:\nMENU\nORDER\nPAY\nHELP")
        else:
            response.message("❓ Unknown command. Reply MENU.")
        
        return str(response)

    finally:
        db.close()
