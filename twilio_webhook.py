from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from database import SessionLocal
from models import Order
from typing import Dict

router = APIRouter()

# In-memory sessions to track orders per phone
sessions: Dict[str, Dict] = {}

MENU_ITEMS = {
    "BURGER": 500,
    "FRIES": 200
}

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    phone = From.replace("whatsapp:", "").strip()
    user_msg = Body.strip().upper()
    response = MessagingResponse()
    
    if phone not in sessions:
        sessions[phone] = {"items": [], "order_started": False}

    session = sessions[phone]

    if user_msg == "MENU":
        menu_text = "🍽 MENU\n" + "\n".join([f"{k} – {v}" for k, v in MENU_ITEMS.items()]) + "\n\nReply ORDER to proceed."
        response.message(menu_text)

    elif user_msg == "ORDER":
        session["order_started"] = True
        session["items"] = []
        response.message("🛒 Order started! Reply with the item names to add them to your order.\nReply PAY when done.")

    elif user_msg == "PAY":
        if session["items"]:
            total = sum(MENU_ITEMS[item] for item in session["items"])
            db = SessionLocal()
            order = Order(
                customer_phone=phone,
                items=", ".join(session["items"]),
                amount=total
            )
            db.add(order)
            db.commit()
            response.message(f"✅ Order confirmed!\nItems: {', '.join(session['items'])}\nTotal: Ksh {total}\n\nYou will receive an M-Pesa prompt shortly.")
            sessions[phone] = {"items": [], "order_started": False}
        else:
            response.message("⚠️ You haven't added any items yet. Reply with item names from MENU.")

    elif session["order_started"] and user_msg in MENU_ITEMS:
        session["items"].append(user_msg)
        response.message(f"✅ {user_msg} added to your order. Reply PAY when done or add more items from MENU.")

    else:
        response.message("❓ Unknown command. Reply MENU to see available commands.")

    return str(response)
