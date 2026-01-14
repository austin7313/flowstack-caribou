from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    incoming = Body.strip().lower()
    twiml = MessagingResponse()

    if incoming in ["hi", "hello", "hey"]:
        twiml.message(
            "👋 Welcome to FlowStack!\n\n"
            "Reply MENU to see options."
        )
    elif incoming == "menu":
        twiml.message(
            "🍽 MENU\n"
            "Burger – 500\n"
            "Fries – 200\n\n"
            "Reply ORDER to proceed."
        )
    else:
        twiml.message("❓ Unknown command. Reply MENU.")

    xml = str(twiml)

    return PlainTextResponse(
        content=xml,
        media_type="text/xml",
        headers={
            "Content-Type": "text/xml",
            "Content-Encoding": "identity",
            "Cache-Control": "no-store"
        }
    )
