from fastapi import FastAPI
from twilio_webhook import router as whatsapp_router
from database import Base, engine

app = FastAPI(title="FlowStack Backend")

# Create SQLite tables
Base.metadata.create_all(bind=engine)

# Include WhatsApp router
app.include_router(whatsapp_router, prefix="/webhook")

@app.get("/")
def health():
    return {"status": "FlowStack backend running"}
