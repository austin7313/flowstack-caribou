from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from database import SessionLocal
from models import Order

router = APIRouter()

# Simple menu items
MENU_ITEMS = {
    "BURGER": 500,
    "FRIES": 200
}

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    db = SessionLocal()

    body_text = Body.strip().upper()
    response = MessagingResponse()

    # Handle MENU command
    if body_text == "MENU":
        menu_text = "🍽 MENU\n"
        for item, price in MENU_ITEMS.items():
            menu_text += f"{item.capitalize()} – {price}\n"
        menu_text += "\nReply ORDER to proceed."
        response.message(menu_text)
        return str(response)

    # Handle ORDER command (ask for item)
    elif body_text == "ORDER":
        response.message("✅ Please type the item you want to order from the MENU.")
        return str(response)

    # Handle item order
    elif body_text in MENU_ITEMS:
        order = Order(
            customer_phone=From.replace("whatsapp:", ""),
            items=body_text.capitalize(),
            amount=MENU_ITEMS[body_text]
        )
        db.add(order)
        db.commit()
        response.message(
            f"✅ Order received: {body_text.capitalize()} – {MENU_ITEMS[body_text]} Ksh\n"
            "Reply PAY to receive M-Pesa prompt."
        )
        return str(response)

    # Handle unknown commands
    else:
        response.message("❓ Unknown command. Reply MENU.")
        return str(response)
