from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_phone = Column(String, index=True)
    customer_name = Column(String, nullable=True)
    items = Column(String)
    amount = Column(Float)
    status = Column(String, default="awaiting_payment")
    created_at = Column(DateTime, default=datetime.utcnow)
