import uvicorn
import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import init_db, get_db
from app.crud import create_payment, mark_payment_successful, calculate_fee, get_active_parking_session, get_payment_status
from app.schemas import PaymentRequest, PaymentResponse
from fastapi import Query
from app.crud import get_all_payments_and_sessions
from app.services import get_payment_plan_status
import logging

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Payment Service", version="1.0.1")

@app.on_event("startup")
async def on_startup():
    await init_db()


@app.post("/ps/api/v1/payments/", response_model=PaymentResponse)
async def process_payment(request: PaymentRequest, db: AsyncSession = Depends(get_db)):
    try:
        logging.info(f"Received payment request for plate: {request.plate_number}")

        is_plan_active = await get_payment_plan_status(request.plate_number)
        logging.info(f"DEBUG MODE: Payment plan status for {request.plate_number}: {is_plan_active}")

        # Determine parking session ID
        parking_session_id = request.parking_session_id
        if request.source == "website" or not parking_session_id:
            logging.info(f"Fetching active session for plate: {request.plate_number}")
            parking_session_id = await get_active_parking_session(db, request.plate_number)
            if not parking_session_id:
                logging.error(f"No active session found for plate: {request.plate_number}")
                raise HTTPException(status_code=404, detail="No active parking session found for this plate number.")

        # Calculate fee
        fee = await calculate_fee(db, parking_session_id)
        if fee is None:
            raise HTTPException(status_code=404, detail="Vehicle already exited.")

        # Check if already paid
        if await get_payment_status(db, parking_session_id):
            note = f"Payment already made for session {parking_session_id}. No fee charged."
            logging.info(note)
            await create_payment(db, parking_session_id, 0.0, request.source or "gate", note)

            return PaymentResponse(
                status="already_paid",
                message="Payment has already been made for this session. No fee charged.",
                parking_session_id=parking_session_id,
                fee=0.0,
                is_paid=True
            )

        # Handle active plan logic
        if is_plan_active:
            if request.source == "website":
                note = (
                    f"User of vehicle {request.plate_number} tried to pay via website, "
                    "but has an active payment plan. Payment is handled automatically at the gate."
                )
                logging.info(note)
                raise HTTPException(
                    status_code=400,
                    detail="Payment is already covered by the subscription plan."
                )
            else:  # source is gate
                note = (
                    f"User of vehicle {request.plate_number} exited via gate with an active payment plan. "
                    "No manual payment required — covered by the plan."
                )
                logging.info(note)
                await create_payment(db, parking_session_id, fee, "gate", note)

                if await mark_payment_successful(db, parking_session_id):
                    return PaymentResponse(
                        status="success",
                        message="Exit allowed under active payment plan.",
                        parking_session_id=parking_session_id,
                        fee=fee,
                        is_paid=True
                    )
                else:
                    raise HTTPException(status_code=500, detail="Failed to mark payment as successful.")

        # Fallback: Normal payment flow
        note = f"User of vehicle {request.plate_number} made a payment of {fee} via {request.source or 'gate'}."
        await create_payment(db, parking_session_id, fee, request.source or "gate", note)

        if request.source == "website":
            if await mark_payment_successful(db, parking_session_id):
                return PaymentResponse(
                    status="success",
                    message="Payment successful via website.",
                    parking_session_id=parking_session_id,
                    fee=fee,
                    is_paid=True
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to update payment status.")

        return PaymentResponse(
            status="failed",
            message="No active payment plan. Please activate your plan or pay via website.",
            parking_session_id=parking_session_id,
            fee=fee,
            is_paid=False
        )

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/ps/api/v1/history/", response_model=dict)
async def get_payment_and_session_history(
        plate_number: str = Query(..., description="License plate number to fetch payment and parking history."),
        db: AsyncSession = Depends(get_db)
):
    try:
        logging.info(f"Fetching history for plate: {plate_number}")
        history = await get_all_payments_and_sessions(db, plate_number)

        if not history["history"]:
            logging.warning(f"No records found for plate: {plate_number}")
            raise HTTPException(status_code=404, detail="No records found for this plate number.")

        return history
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logging.error(f"Unexpected error while fetching history: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PAYMENT_SERVICE_PORT", 8001)), reload=True)
