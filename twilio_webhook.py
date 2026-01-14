from fastapi import APIRouter, Request, Response
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    # Just read the body so FastAPI doesn't error
    _ = await request.body()

    twiml = MessagingResponse()
    twiml.message("✅ FlowStack is LIVE and responding on WhatsApp")

    return Response(
        content=str(twiml),
        media_type="application/xml"
    )
