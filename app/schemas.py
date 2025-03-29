from pydantic import BaseModel
from typing import Optional, List

class PaymentDetail(BaseModel):
    payment_id: int
    amount: float
    is_paid: bool
    payment_timestamp: str
    payment_source: str
    note: str

class ParkingSessionDetail(BaseModel):
    session_id: int
    license_plate: str
    entry_timestamp: str
    exit_timestamp: Optional[str] = None
    is_active: bool
    payments: List[PaymentDetail]

class HistoryResponse(BaseModel):
    history: List[ParkingSessionDetail]

class PaymentRequest(BaseModel):
    plate_number: str  # Ensure this is first
    parking_session_id: Optional[int] = None
    source: Optional[str] = None  # Optional field

class PaymentResponse(BaseModel):
    status: str
    message: str
    parking_session_id: int
    fee: float
    is_paid: bool
