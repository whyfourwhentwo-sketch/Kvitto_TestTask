from errors import InvalidPromo
from tariffs import PROMO_CODES


def calculate(price: int, promo_code: str | None) -> tuple[int, int]:
    """Возвращает (amount, discount) в копейках."""
    if promo_code is None:
        return price, 0
    percent = PROMO_CODES.get(promo_code)
    if percent is None:
        raise InvalidPromo
    discount = price * percent // 100  # только целые, без float
    return price - discount, discount