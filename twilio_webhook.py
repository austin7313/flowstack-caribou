from fastapi import APIRouter, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    incoming_msg = form.get("Body", "").lower()

    resp = MessagingResponse()

    if incoming_msg.startswith("join"):
        resp.message("✅ Sandbox connected. CHATPESA is live.")
    else:
        resp.message("CHATPESA active. Send HELP.")

    return Response(content=str(resp), media_type="application/xml")
