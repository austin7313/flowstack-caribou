from fastapi import FastAPI
from database import engine, Base
from twilio_webhook import router as whatsapp_router

app = FastAPI(title="FlowStack Backend")

# Create tables in DB
Base.metadata.create_all(bind=engine)

# Include Twilio WhatsApp router
app.include_router(whatsapp_router, prefix="/webhook")

@app.get("/")
def health():
    return {"status": "FlowStack backend running"}
