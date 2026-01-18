from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    incoming_msg = form.get("Body", "").strip().lower()
    from_number = form.get("From")

    resp = MessagingResponse()

    if incoming_msg.startswith("join"):
        resp.message("✅ ChatPESA connected. You can now receive payments on WhatsApp.")
    else:
        resp.message("👋 ChatPESA is live. Payments coming next.")

    return PlainTextResponse(str(resp), media_type="application/xml")
