from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI(title="ChatPESA")

@app.get("/")
def root():
    return {"status": "CHATPESA alive"}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    incoming_msg = form.get("Body", "").strip().lower()

    resp = MessagingResponse()

    if incoming_msg.startswith("join"):
        resp.message("✅ ChatPESA connected. Payments coming next.")
    else:
        resp.message("👋 ChatPESA is live.")

    return PlainTextResponse(str(resp), media_type="application/xml")
