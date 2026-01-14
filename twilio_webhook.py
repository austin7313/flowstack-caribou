from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from database import SessionLocal
from models import Order
import random

router = APIRouter()

# Sample menu
MENU_ITEMS = {
    "Burger": 500,
    "Fries": 200,
    "Pizza": 800,
    "Soda": 100
}

def format_menu():
    menu_text = "🍽 *MENU*\n"
    for item, price in MENU_ITEMS.items():
        menu_text += f"{item} – {price} Ksh\n"
    menu_text += "\nReply *ORDER* to place an order."
    return menu_text

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    user_msg = Body.strip().lower()
    phone_number = From.replace("whatsapp:", "")
    db = SessionLocal()
    response = MessagingResponse()

    try:
        # HELP command
        if user_msg == "help":
            response.message(
                "📋 Commands:\n"
                "- MENU → Show menu\n"
                "- ORDER → Place an order\n"
                "- STATUS <order_id> → Check order status\n"
                "- HELP → Show this message"
            )
            return str(response)

        # MENU command
        elif user_msg == "menu":
            response.message(format_menu())
            return str(response)

        # ORDER command
        elif user_msg.startswith("order"):
            # For simplicity, we treat the whole body as order items
            items_text = Body[6:].strip() if len(Body) > 5 else "Burger"  # default if nothing
            amount = sum(MENU_ITEMS.get(item.capitalize(), 0) for item in items_text.split(","))

            # Generate random order ID
            order_id = random.randint(1000, 9999)

            order = Order(
                customer_phone=phone_number,
                items=items_text,
                amount=amount,
                status="Pending",
                order_id=order_id
            )
            db.add(order)
            db.commit()

            # Placeholder for M-Pesa payment link
            mpesa_link = f"https://mpesa.fake/pay?order={order_id}&amount={amount}"

            response.message(
                f"✅ Order received!\n"
                f"Order ID: {order_id}\n"
                f"Total: {amount} Ksh\n"
                f"Pay here: {mpesa_link}\n\n"
                f"Reply STATUS {order_id} to check your order."
            )
            return str(response)

        # STATUS command
        elif user_msg.startswith("status"):
            try:
                _, oid = user_msg.split()
                oid = int(oid)
            except:
                response.message("❌ Invalid order ID. Use: STATUS <order_id>")
                return str(response)

            order = db.query(Order).filter(Order.order_id == oid).first()
            if order:
                response.message(
                    f"📦 Order Status:\n"
                    f"Order ID: {order.order_id}\n"
                    f"Items: {order.items}\n"
                    f"Amount: {order.amount} Ksh\n"
                    f"Status: {order.status}"
                )
            else:
                response.message("❌ Order not found.")
            return str(response)

        # Unknown command
        else:
            response.message("❓ Unknown command. Reply MENU to see options.")
            return str(response)

    finally:
        db.close()
