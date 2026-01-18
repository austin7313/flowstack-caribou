from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from twilio_webhook import router as whatsapp_router

app = FastAPI(title="ChatPESA")

# Health check (VERY important)
@app.get("/")
def root():
    return {"status": "ChatPESA live"}

# Register WhatsApp webhook
app.include_router(whatsapp_router)
