from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from database import SessionLocal
from models import Order

router = APIRouter()

# Simple menu
MENU_TEXT = "🍽 MENU\nBurger – 500\nFries – 200\n\nReply ORDER to proceed."

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    db = SessionLocal()
    message = Body.strip().lower()
    response = MessagingResponse()

    if message == "menu":
        response.message(MENU_TEXT)
    elif message == "order":
        response.message("✅ Please reply with your item (e.g., Burger or Fries).")
    elif message in ["burger", "fries"]:
        amount = 500 if message == "burger" else 200
        order = Order(
            customer_phone=From.replace("whatsapp:", ""),
            items=message,
            amount=amount
        )
        db.add(order)
        db.commit()
        response.message(f"✅ Order received for {message.title()} ({amount} Ksh).")
    else:
        response.message("❓ Unknown command. Reply MENU.")

    db.close()
    return str(response)
