from fastapi import APIRouter, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    body = form.get("Body", "").lower()

    resp = MessagingResponse()

    if body.startswith("join"):
        resp.message("✅ Sandbox connected. CHATPESA is live.")
    else:
        resp.message("CHATPESA active. Send JOIN CHATPESA")

    return Response(str(resp), media_type="application/xml")
