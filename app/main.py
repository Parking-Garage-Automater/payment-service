import uvicorn
import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import init_db, get_db
from app.crud import create_payment, mark_payment_successful, calculate_fee
from app.schemas import PaymentRequest, PaymentResponse

app = FastAPI(title="Payment Service", version="1.0.0")

@app.on_event("startup")
async def on_startup():
    """Initialize database on service startup."""
    await init_db()

@app.post("/api/v1/payments/", response_model=PaymentResponse)
async def process_payment(request: PaymentRequest, db: AsyncSession = Depends(get_db)):
    """Handles payment processing based on parking session ID & plate number."""
    try:
        # Calculate parking fee using session entry time
        fee = await calculate_fee(db, request.parking_session_id)
        if fee is None:
            raise HTTPException(status_code=404, detail="Parking session not found or already exited.")

        # Simulate external payment processing (replace with actual API call)
        external_payment_success = True  # Simulating successful payment

        if not external_payment_success:
            raise HTTPException(status_code=402, detail="External payment failed.")

        # Create payment record
        payment = await create_payment(db, request.parking_session_id, fee)

        # Mark the payment as successful
        updated_payment = await mark_payment_successful(db, request.parking_session_id)
        if not updated_payment:
            raise HTTPException(status_code=500, detail="Payment could not be marked as paid.")

        return PaymentResponse(
            status="success",
            message="Payment successful",
            parking_session_id=request.parking_session_id,
            amount=fee,  # Send the calculated fee
            is_paid=True
        )

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PAYMENT_SERVICE_PORT", 8001)), reload=True)
