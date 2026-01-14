from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from database import SessionLocal
from models import Order, User

router = APIRouter()

MENU_ITEMS = {
    "Burger": 500,
    "Fries": 200,
    "Pizza": 800
}

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    phone = From.replace("whatsapp:", "")
    message = Body.strip().lower()
    db = SessionLocal()
    resp = MessagingResponse()

    # Get or create user
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone, stage="start", order_items="")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Load user state
    stage = user.stage
    order_items = user.order_items.split(",") if user.order_items else []

    # Command handling
    if message == "menu":
        menu_text = "🍽 MENU\n" + "\n".join([f"{k} – {v} Ksh" for k, v in MENU_ITEMS.items()])
        menu_text += "\n\nReply ORDER to start ordering."
        user.stage = "menu_shown"
        resp.message(menu_text)

    elif message == "order":
        if stage in ["menu_shown", "start"]:
            user.stage = "ordering"
            resp.message("Reply with item names separated by commas. Example:\nBurger, Fries")
        else:
            resp.message("❗ You need to see the MENU first. Reply MENU.")

    elif stage == "ordering":
        items = [item.strip().title() for item in Body.split(",") if item.strip().title() in MENU_ITEMS]
        if not items:
            resp.message("❌ Invalid items. Reply with correct item names from the MENU.")
        else:
            total_amount = sum([MENU_ITEMS[i] for i in items])
            order_items.extend(items)
            user.stage = "order_confirmed"
            user.order_items = ",".join(order_items)

            # Save order
            order = Order(customer_phone=phone, items=",".join(order_items), amount=total_amount)
            db.add(order)
            db.commit()

            resp.message(f"✅ Order received:\n{', '.join(order_items)}\nTotal: {total_amount} Ksh\n\nReply PAY to get M-Pesa prompt.")

    elif message == "pay":
        if stage == "order_confirmed":
            resp.message("💳 M-Pesa payment link or instructions here.")
            user.stage = "paid"
        else:
            resp.message("❗ You need to place an ORDER first.")

    elif message == "help":
        resp.message("ℹ️ Commands:\nMENU - see menu\nORDER - place order\nPAY - pay for order\nHELP - this message")

    else:
        resp.message("❓ Unknown command. Reply MENU.")

    db.commit()
    db.close()
    return str(resp)
