from fastapi import FastAPI
from twilio_webhook import router as whatsapp_router

app = FastAPI()

app.include_router(whatsapp_router, prefix="/webhook")

@app.get("/")
def root():
    return {"status": "FlowStack backend running"}
