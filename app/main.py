import uvicorn
import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import init_db, get_db
from app.crud import create_payment, mark_payment_successful, calculate_fee, get_active_parking_session, get_payment_status
from app.schemas import PaymentRequest, PaymentResponse
from fastapi import Query
from app.crud import get_all_payments_and_sessions
from app.services import get_payment_plan_status  # Import API function
import logging

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Payment Service", version="1.0.0")

@app.on_event("startup")
async def on_startup():
    await init_db()


@app.post("/api/v1/payments/", response_model=PaymentResponse)
async def process_payment(request: PaymentRequest, db: AsyncSession = Depends(get_db)):
    try:
        logging.info(f"Received payment request for plate: {request.plate_number}")

        is_plan_active = True
        logging.info(f"DEBUG MODE: Payment plan status for {request.plate_number}: {is_plan_active}")

        parking_session_id = request.parking_session_id
        if request.source == "website" or parking_session_id is None:
            logging.info(f"Fetching active session for plate: {request.plate_number}")
            parking_session_id = await get_active_parking_session(db, request.plate_number)
            logging.info(f"Fetched parking session ID: {parking_session_id}")
            if parking_session_id is None:
                logging.error(f"No active session found for plate: {request.plate_number}")
                raise HTTPException(status_code=404, detail="No active parking session found for this plate number.")

        if is_plan_active and request.source != "website":
            note = f"User of vehicle {request.plate_number} tried to pay via gate but has an active plan."
            logging.info(note)

            await create_payment(db, parking_session_id, 0.0, "gate", note)

            updated_payment = await mark_payment_successful(db, parking_session_id)
            if updated_payment:
                return PaymentResponse(
                    status="success",
                    message="Exit allowed under active payment plan.",
                    parking_session_id=parking_session_id,
                    fee=0.0,
                    is_paid=True
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to mark payment as successful.")

        is_already_paid = await get_payment_status(db, parking_session_id)
        if is_already_paid:
            note = f"Payment already made for session {parking_session_id}. No fee charged."
            logging.info(note)

            await create_payment(db, parking_session_id, 0.0, request.source or "gate", note)
            return PaymentResponse(
                status="already_paid",
                message="Payment has already been made for this session before. No fee charged.",
                parking_session_id=parking_session_id,
                fee=0.0,
                is_paid=True
            )

        fee = await calculate_fee(db, parking_session_id)
        if fee is None:
            raise HTTPException(status_code=404, detail="Parking session not found or already exited.")

        if is_plan_active and request.source == "website":
            note = f"User of vehicle {request.plate_number} tried to pay via website but has an active plan."
            logging.info(note)
            raise HTTPException(status_code=400, detail="Payment is already covered by the subscription plan.")

        note = f"User of vehicle {request.plate_number} made a payment of {fee} via {request.source or 'gate'}."
        await create_payment(db, parking_session_id, fee, request.source or "gate", note)

        if request.source == "website":
            updated_payment = await mark_payment_successful(db, parking_session_id)
            if updated_payment:
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
            message="You did not have an active payment plan. Please activate your payment plan or pay through our website.",
            parking_session_id=parking_session_id,
            fee=fee,
            is_paid=False
        )

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/api/v1/history/", response_model=dict)
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
