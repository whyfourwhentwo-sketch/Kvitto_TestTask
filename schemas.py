from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from config import INSTALLMENT_MONTHS
from enums import PaymentMethod, PaymentStatus
from tariffs import TariffId


class TariffOut(BaseModel):
    id: TariffId
    title: str
    price: int


class PaymentCreate(BaseModel):
    tariff_id: TariffId
    email: EmailStr
    method: PaymentMethod
    installment_months: int | None = None
    promo_code: str | None = None

    @field_validator("promo_code")
    @classmethod
    def normalize_promo(cls, v: str | None) -> str | None:
        return v.strip().lower() if v is not None else None

    @model_validator(mode="after")
    def check_installment(self):
        if self.method == PaymentMethod.INSTALLMENT:
            if self.installment_months not in INSTALLMENT_MONTHS:
                raise ValueError(f"installment_months must be one of {INSTALLMENT_MONTHS}")
        elif self.installment_months is not None:
            raise ValueError("installment_months is allowed only for installment")
        return self


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PaymentStatus
    tariff_id: TariffId
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None = None  # заполняет сервис
    email: str
    created_at: datetime


class WebhookIn(BaseModel):
    payment_id: int
    status: PaymentStatus


class WebhookOut(BaseModel):
    result: Literal["ok"] = "ok"