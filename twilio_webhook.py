from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from database import SessionLocal
from models import Order

router = APIRouter()

# Simple menu
MENU_ITEMS = {
    "Burger": 500,
    "Fries": 200,
    "Pizza": 800
}

# Track user state in memory (for demo; for production, use DB or Redis)
USER_STATE = {}

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    phone = From.replace("whatsapp:", "")
    message = Body.strip().lower()
    db = SessionLocal()
    resp = MessagingResponse()

    # Initialize user state if not exists
    if phone not in USER_STATE:
        USER_STATE[phone] = {"stage": "start", "order_items": []}

    state = USER_STATE[phone]

    # Command handling
    if message in ["menu"]:
        menu_text = "🍽 MENU\n" + "\n".join([f"{k} – {v} Ksh" for k, v in MENU_ITEMS.items()])
        menu_text += "\n\nReply ORDER to start ordering."
        state["stage"] = "menu_shown"
        resp.message(menu_text)

    elif message == "order":
        if state["stage"] in ["menu_shown", "start"]:
            items_text = "Reply with item names separated by commas. Example:\nBurger, Fries"
            state["stage"] = "ordering"
            resp.message(items_text)
        else:
            resp.message("❗ You need to see the MENU first. Reply MENU.")

    elif state["stage"] == "ordering":
        # Save items
        items = [item.strip().title() for item in Body.split(",") if item.strip().title() in MENU_ITEMS]
        if not items:
            resp.message("❌ Invalid items. Reply with correct item names from the MENU.")
        else:
            state["order_items"] = items
            total_amount = sum([MENU_ITEMS[i] for i in items])
            state["stage"] = "order_confirmed"

            # Save to DB
            order = Order(customer_phone=phone, items=", ".join(items), amount=total_amount)
            db.add(order)
            db.commit()

            resp.message(f"✅ Order received:\n{', '.join(items)}\nTotal: {total_amount} Ksh\n\nReply PAY to get M-Pesa prompt.")

    elif message == "pay":
        if state["stage"] == "order_confirmed":
            resp.message("💳 M-Pesa payment link or instructions here.")
            state["stage"] = "paid"
        else:
            resp.message("❗ You need to place an ORDER first.")

    elif message == "help":
        resp.message("ℹ️ Commands:\nMENU - see menu\nORDER - place order\nPAY - pay for order\nHELP - this message")

    else:
        resp.message("❓ Unknown command. Reply MENU.")

    db.close()
    return str(resp)
