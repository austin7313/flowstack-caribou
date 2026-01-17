from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twilio_webhook import router as whatsapp_router

app = FastAPI(
    title="ChatPESA",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    whatsapp_router,
    prefix="/webhook",
    tags=["WhatsApp"]
)

@app.get("/")
def health():
    return {
        "status": "ChatPESA alive",
        "webhook": "/webhook/whatsapp"
    }
