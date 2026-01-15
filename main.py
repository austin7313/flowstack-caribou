from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twilio_webhook import router as whatsapp_router

app = FastAPI(
    title="FlowStack Backend",
    description="WhatsApp tells businesses what to do next",
    version="1.0.0"
)

# Allow dashboard + external tools later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WhatsApp webhook routes
app.include_router(
    whatsapp_router,
    prefix="/webhook",
    tags=["WhatsApp"]
)

@app.get("/")
def health_check():
    """
    Render health check endpoint
    """
    return {
        "status": "✅ FlowStack is running",
        "webhook": "/webhook/whatsapp",
        "commands": ["hi", "hello", "hey", "menu", "order"]
    }
