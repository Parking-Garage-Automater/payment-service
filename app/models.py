from sqlalchemy import Column, Integer, Numeric, Boolean, TIMESTAMP, String
from datetime import datetime
from app.database import Base

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parking_session_id = Column(Integer, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    is_paid = Column(Boolean, default=False)
    payment_timestamp = Column(TIMESTAMP, default=datetime.utcnow)

class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    license_plate = Column(String(20), nullable=False)
    entry_timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    exit_timestamp = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True)
