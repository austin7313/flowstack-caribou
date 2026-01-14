from fastapi import APIRouter, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    incoming = Body.strip().lower()
    response = MessagingResponse()

    if incoming in ["hi", "hello", "hey"]:
        response.message(
            "👋 Welcome to FlowStack!\n\n"
            "Reply:\n"
            "MENU – View items\n"
            "ORDER – Place an order\n"
            "HELP – Talk to support"
        )

    elif incoming == "menu":
        response.message(
            "🍽️ TODAY'S MENU\n\n"
            "• Burger – KES 500\n"
            "• Fries – KES 200\n"
            "• Soda – KES 150\n\n"
            "Reply ORDER to continue."
        )

    elif incoming == "order":
        response.message(
            "📝 Please reply with your order.\n\n"
            "Example:\nBurger + Fries"
        )

    elif incoming == "help":
        response.message(
            "📞 Support will reach out shortly.\n"
            "Thank you for using FlowStack."
        )

    else:
        response.message(
            "❓ I didn’t understand that.\n\n"
            "Reply MENU, ORDER or HELP."
        )

    return Response(
        content=str(response),
        media_type="application/xml"
    )
