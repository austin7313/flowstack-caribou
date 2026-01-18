from fastapi import FastAPI
from twilio_webhook import router

app = FastAPI()

app.include_router(router)

@app.get("/")
def root():
    return {"status": "CHATPESA alive"}
