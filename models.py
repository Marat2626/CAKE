from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base

class Cake(Base):
    __tablename__ = "cakes"
    id = Column(Integer, primary_key=True)
    name = Column(String, 	nullable=False)
    description = Column(Text)
    price = Column(Float, 	nullable=False)
    weight = Column(Float, default=1.0)
    persons = Column(String)
    image_url = Column(String)
    category = Column(String)
    is_available = Column(Boolean, 	default=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    cake_id = Column(Integer, ForeignKey("cakes.id"), nullable=False)
    customer_name = Column(String, 	nullable=False)
    phone = Column(String, 	nullable=False)
    message = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
