import os
import requests
import base64
from datetime import datetime

DARAJA_CONSUMER_KEY = os.environ.get("DARAJA_CONSUMER_KEY")
DARAJA_CONSUMER_SECRET = os.environ.get("DARAJA_CONSUMER_SECRET")

def get_access_token():
    auth = base64.b64encode(
        f"{DARAJA_CONSUMER_KEY}:{DARAJA_CONSUMER_SECRET}".encode()
    ).decode()

    headers = {"Authorization": f"Basic {auth}"}
    res = requests.get(
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        headers=headers
    )
    return res.json()["access_token"]
