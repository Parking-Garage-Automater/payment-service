from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from app.models import PaymentTransaction, ParkingSession
from datetime import datetime
import math

async def calculate_fee(db: AsyncSession, session_id: int):
    """Fetch session details and calculate parking fee."""
    try:
        result = await db.execute(
            select(ParkingSession).where(ParkingSession.id == session_id, ParkingSession.is_active == True)
        )
        session = result.scalars().first()

        if not session:
            return None  # No active session found

        # Calculate duration in minutes (round down)
        duration_minutes = math.floor((datetime.utcnow() - session.entry_timestamp).total_seconds() / 60)
        fee = min(max(1, duration_minutes * 0.5), 10)  # Min 1, Max 10

        return round(fee, 2)
    except SQLAlchemyError as e:
        await db.rollback()
        raise e

async def create_payment(db: AsyncSession, session_id: int, amount: float):
    """Create a new payment transaction."""
    try:
        new_payment = PaymentTransaction(parking_session_id=session_id, amount=amount, is_paid=False)
        db.add(new_payment)
        await db.flush()
        await db.refresh(new_payment)
        await db.commit()
        return new_payment
    except SQLAlchemyError as e:
        await db.rollback()
        raise e

async def get_payment(db: AsyncSession, session_id: int):
    """Retrieve a payment record by parking session ID."""
    result = await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.parking_session_id == session_id)
    )
    return result.scalars().first()

async def mark_payment_successful(db: AsyncSession, session_id: int):
    """Update a payment record as paid."""
    try:
        result = await db.execute(
            select(PaymentTransaction).where(PaymentTransaction.parking_session_id == session_id)
        )
        payment = result.scalars().first()

        if payment and not payment.is_paid:
            payment.is_paid = True
            await db.commit()
            return payment
        return None
    except SQLAlchemyError as e:
        await db.rollback()
        raise e
