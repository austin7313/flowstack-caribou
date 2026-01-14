from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    response = MessagingResponse()

    response.message(
        "👋 Hi! This is FlowStack.\n\n"
        "We received your message:\n"
        f"\"{Body}\"\n\n"
        "✅ WhatsApp integration is working."
    )

    return str(response)
