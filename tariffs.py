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
    TariffId.BASIC: Tariff("Basic", 9900_00),
    TariffId.STANDARD: Tariff("Standard", 19900_00),
    TariffId.PREMIUM: Tariff("Premium", 29900_00),
}

# код в нижнем регистре -> скидка в процентах
PROMO_CODES: dict[str, int] = {"kvitto10": 10}