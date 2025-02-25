from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from app.models import PaymentTransaction, ParkingSession
from datetime import datetime
import math
import logging

logging.basicConfig(level=logging.INFO)

async def calculate_fee(db: AsyncSession, session_id: int):
    logging.info(f"Fetching parking session for ID: {session_id}")

    result = await db.execute(
        select(ParkingSession).where(ParkingSession.id == session_id, ParkingSession.is_active == True)
    )
    session = result.scalars().first()

    if not session:
        logging.error(f"Session {session_id} not found or inactive.")
        return None

    duration_minutes = (datetime.utcnow() - session.entry_timestamp).total_seconds() // 60
    fee = min(max(1, duration_minutes * 0.5), 10)

    logging.info(f"Calculated fee for session {session_id}: {fee}")
    return round(fee, 2)


async def create_payment(db: AsyncSession, session_id: int, amount: float, payment_source: str = "gate"):
    try:
        new_payment = PaymentTransaction(
            parking_session_id=session_id,
            amount=amount,
            is_paid=False,
            payment_source=payment_source
        )
        db.add(new_payment)
        await db.commit()
        await db.refresh(new_payment)
        return new_payment
    except SQLAlchemyError as e:
        await db.rollback()
        raise e

async def get_payment(db: AsyncSession, session_id: int):
    result = await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.parking_session_id == session_id)
    )
    return result.scalars().first()

async def mark_payment_successful(db: AsyncSession, session_id: int):
    try:
        result = await db.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.parking_session_id == session_id, PaymentTransaction.is_paid == False)
            .order_by(PaymentTransaction.payment_timestamp.desc())
        )
        payment = result.scalars().first()

        if payment:
            payment.is_paid = True
            await db.commit()
            return payment
        return None
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def get_active_parking_session(db: AsyncSession, plate_number: str):
    logging.info(f"Searching for active session for plate number: {plate_number}")

    result = await db.execute(
        select(ParkingSession.id)
        .where(ParkingSession.license_plate == plate_number, ParkingSession.is_active == True)
        .order_by(ParkingSession.entry_timestamp.desc())
    )

    session_id = result.scalars().first()

    if session_id is None:
        logging.warning(f"No active session found for plate: {plate_number}")
    else:
        logging.info(f"Found active session ID: {session_id} for plate: {plate_number}")

    return session_id

async def get_payment_status(db: AsyncSession, session_id: int):
    result = await db.execute(
        select(PaymentTransaction.is_paid)
        .where(PaymentTransaction.parking_session_id == session_id, PaymentTransaction.is_paid == True)
    )
    payment = result.scalars().first()

    return payment is not None




