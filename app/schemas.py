from pydantic import BaseModel

class PaymentRequest(BaseModel):
    parking_session_id: int
    plate_number: str

class PaymentResponse(BaseModel):
    status: str
    message: str
    parking_session_id: int
    amount: float
    is_paid: bool
