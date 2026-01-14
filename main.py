from fastapi import FastAPI
from database import engine, Base
from twilio_webhook import router as whatsapp_router

app = FastAPI(title="FlowStack Backend")

# Create database tables
Base.metadata.create_all(bind=engine)

# Include WhatsApp webhook router
app.include_router(whatsapp_router, prefix="/webhook")

@app.get("/")
def health():
    return {"status": "FlowStack backend running"}
