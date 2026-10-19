from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

import service
from db import get_db
from schemas import PaymentCreate, PaymentOut, TariffOut, WebhookIn, WebhookOut
from tariffs import TARIFFS

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


@router.get("/tariffs", response_model=list[TariffOut])
def list_tariffs():
    return [TariffOut(id=tid, title=t.title, price=t.price) for tid, t in TARIFFS.items()]


@router.post("/payments", response_model=PaymentOut, status_code=201)
def create_payment(
    payload: PaymentCreate,
    response: Response,
    db: DB,
    idempotency_key: Annotated[str | None, Header()] = None,
):
    payment, created = service.create_payment(db, payload, idempotency_key)
    if not created:
        response.status_code = 200
    return service.to_out(payment)


@router.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: DB):
    return service.to_out(service.get_payment(db, payment_id))


@router.post("/webhooks/bank", response_model=WebhookOut)
def bank_webhook(payload: WebhookIn, db: DB):
    service.apply_webhook(db, payload.payment_id, payload.status)
    return WebhookOut()