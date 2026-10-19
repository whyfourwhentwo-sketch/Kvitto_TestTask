import pytest

from errors import InvalidPromo
from pricing import calculate
from tariffs import TARIFFS, TariffId


def test_no_promo():
    assert calculate(100_000, None) == (100_000, 0)


def test_promo_10_percent():
    assert calculate(100_000, "sale10") == (90_000, 10_000)


def test_discount_rounds_down():
    # 10% от 9999 = 999.9 -> 999
    assert calculate(9_999, "sale10") == (9_000, 999)


def test_invalid_promo():
    with pytest.raises(InvalidPromo):
        calculate(100_000, "nope")


def test_every_tariff_id_has_price():
    assert set(TARIFFS) == set(TariffId)