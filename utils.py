import random

def normalize_text(text: str) -> str:
    return text.strip().lower()

def generate_id(prefix: str) -> str:
    return f"{prefix}{random.randint(100000, 999999)}"
