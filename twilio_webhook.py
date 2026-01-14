from fastapi import APIRouter, Form
from starlette.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    msg = Body.strip().lower()
    twiml = MessagingResponse()

    if msg in ["hi", "hello", "hey"]:
        twiml.message(
            "👋 Welcome to FlowStack!\n\n"
            "Reply MENU to see items."
        )
    elif msg == "menu":
        twiml.message(
            "🍽 MENU\n"
            "Burger – 500\n"
            "Fries – 200\n\n"
            "Reply ORDER to proceed."
        )
    else:
        twiml.message("❓ Unknown command. Reply MENU.")

    xml_response = str(twiml)

    return Response(
        content=xml_response,
        status_code=200,
        headers={
            "Content-Type": "text/xml"
        }
    )
