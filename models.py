from sqlalchemy import Column, Integer, String
from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, unique=True, index=True)  # optional for tracking
    customer_phone = Column(String, index=True)
    items = Column(String)
    amount = Column(Integer)
    status = Column(String, default="Pending")
