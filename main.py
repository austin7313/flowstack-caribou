import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from twilio_webhook import router

app = FastAPI(
    title="FlowStack",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/webhook")

@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "FlowStack backend running"
    }

@app.get("/orders")
def get_orders():
    from supabase_client import supabase
    data = supabase.table("orders").select("*").order("created_at", desc=True).execute()
    return data.data

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
