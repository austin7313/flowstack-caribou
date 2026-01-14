from fastapi import APIRouter
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook():
    response = MessagingResponse()
    response.message("🔥 FlowStack webhook connected successfully")
    return str(response)
