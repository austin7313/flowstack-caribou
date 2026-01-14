from fastapi import APIRouter, Response
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook():
    twiml = MessagingResponse()
    twiml.message("🔥 FlowStack webhook connected successfully")

    return Response(
        content=str(twiml),
        media_type="application/xml"
    )
