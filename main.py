from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twilio_webhook import router as whatsapp_router

app = FastAPI(
    title="FlowStack Backend",
    description="WhatsApp tells businesses what to do next",
    version="1.0.0"
)

# ---------------- CORS ---------------- #
# Allow dashboard + external tools to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set your dashboard domain here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- WEBHOOK ROUTES ---------------- #
app.include_router(
    whatsapp_router,
    prefix="/webhook",
    tags=["WhatsApp"]
)

# ---------------- HEALTH CHECK ---------------- #
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

# ---------------- ORDERS (OPTIONAL DASHBOARD) ---------------- #
@app.get("/orders")
def get_orders():
    """
    Fetch all orders from Supabase (for quick testing)
    """
    from supabase_client import supabase

    try:
        response = supabase.table("orders").select("*").order("created_at", desc=True).execute()
        return {
            "success": True,
            "orders": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------------- LOCAL TESTING ---------------- #
if __name__ == "__main__":
    import uvicorn, os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
