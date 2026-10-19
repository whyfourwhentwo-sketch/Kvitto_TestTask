import pytest

from installments import build_schedule


def test_remainder_goes_to_first_payments():
    assert build_schedule(1000, 3) == [334, 333, 333]


def test_even_split():
    assert build_schedule(900, 3) == [300, 300, 300]


def test_amount_smaller_than_months():
    assert build_schedule(2, 3) == [1, 1, 0]


@pytest.mark.parametrize("amount", [1, 999, 9_999, 100_000, 250_001])
@pytest.mark.parametrize("months", [3, 6, 12])
def test_schedule_properties(amount, months):
    s = build_schedule(amount, months)
    assert len(s) == months
    assert sum(s) == amount
    assert max(s) - min(s) <= 1
    assert s == sorted(s, reverse=True)  # лишние копейки только в начале