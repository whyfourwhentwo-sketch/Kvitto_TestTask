from dataclasses import dataclass
from enum import IntEnum, unique


@unique
class TariffId(IntEnum):
    """
    Айди тарифа против магических чисел
    """
    BASIC = 1
    STANDARD = 2
    PREMIUM = 3


@dataclass(frozen=True)
class Tariff:
    title: str
    price: int  # копейки


TARIFFS: dict[TariffId, Tariff] = {
    TariffId.BASIC: Tariff("Basic", 100_000),
    TariffId.STANDARD: Tariff("Standard", 250_000),
    TariffId.PREMIUM: Tariff("Premium", 500_000),
}

# код в нижнем регистре -> скидка в процентах
PROMO_CODES: dict[str, int] = {"sale10": 10}