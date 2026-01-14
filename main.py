import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twilio_webhook import router as whatsapp_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="FlowStack Backend",
    description="WhatsApp Business OS for African SMEs",
    version="1.0.0"
)

# CORS - Allow dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your dashboard URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WhatsApp webhook routes
app.include_router(whatsapp_router, prefix="/webhook", tags=["WhatsApp"])

@app.get("/")
def health_check():
    """Health check endpoint - Render uses this to verify service is alive"""
    return {
        "status": "✅ FlowStack backend running",
        "service": "WhatsApp Order Automation",
        "restaurant": "CARIBOU KARIBU",
        "endpoints": {
            "health": "/",
            "whatsapp_webhook": "/webhook/whatsapp",
            "orders": "/orders"
        }
    }

@app.get("/orders")
def get_orders():
    """Get all orders from Supabase"""
    from supabase_client import supabase
    
    try:
        response = supabase.table("orders").select("*").order("created_at", desc=True).execute()
        return {
            "success": True,
            "orders": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# For local testing
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
