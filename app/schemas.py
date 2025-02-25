from pydantic import BaseModel
from typing import Optional

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
