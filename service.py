from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from enums import ALLOWED_TRANSITIONS, PaymentStatus
from errors import InvalidTransition, PaymentNotFound
from installments import build_schedule
from models import Payment
from pricing import calculate
from schemas import PaymentCreate, PaymentOut
from tariffs import TARIFFS


def _by_key(db: Session, key: str) -> Payment | None:
    return db.scalar(select(Payment).where(Payment.idempotency_key == key))


def create_payment(db: Session, data: PaymentCreate, key: str | None) -> tuple[Payment, bool]:
    """Возвращает (платёж, создан_ли_новый)."""
    if key and (existing := _by_key(db, key)):
        return existing, False

    amount, discount = calculate(TARIFFS[data.tariff_id].price, data.promo_code)
    payment = Payment(
        idempotency_key=key,
        tariff_id=data.tariff_id,
        email=data.email,
        method=data.method,
        installment_months=data.installment_months,
        amount=amount,
        discount=discount,
    )
    db.add(payment)
    try:
        db.commit()
    except IntegrityError:
        # параллельный запрос с тем же ключом успел раньше
        db.rollback()
        existing = _by_key(db, key) if key else None
        if existing is None:
            raise
        return existing, False
    return payment, True


def get_payment(db: Session, payment_id: int) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise PaymentNotFound
    return payment


def apply_webhook(db: Session, payment_id: int, new_status: PaymentStatus) -> None:
    payment = get_payment(db, payment_id)
    if new_status not in ALLOWED_TRANSITIONS[payment.status]:
        raise InvalidTransition
    payment.status = new_status
    db.commit()


def to_out(payment: Payment) -> PaymentOut:
    out = PaymentOut.model_validate(payment)
    if payment.installment_months:
        out.schedule = build_schedule(payment.amount, payment.installment_months)
    return out