from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db import Base
from enums import PaymentMethod, PaymentStatus


def _enum(e):
    # хранить в БД value ("pending"), а не имя ("PENDING")
    return Enum(e, values_callable=lambda x: [m.value for m in x], native_enum=False)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    tariff_id: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String)
    method: Mapped[PaymentMethod] = mapped_column(_enum(PaymentMethod))
    installment_months: Mapped[int | None] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)      # итог к оплате, копейки
    discount: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[PaymentStatus] = mapped_column(
        _enum(PaymentStatus), default=PaymentStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )