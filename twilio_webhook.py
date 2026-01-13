from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from database import SessionLocal
from models import Order

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    db = SessionLocal()

    order = Order(
        customer_phone=From.replace("whatsapp:", ""),
        items=Body,
        amount=1000
    )

    db.add(order)
    db.commit()

    response = MessagingResponse()
    response.message(
        "✅ Order received!\n\n"
        "Reply PAY to receive M-Pesa prompt."
    )

    return str(response)
