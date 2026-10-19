from enums import ALLOWED_TRANSITIONS, PaymentStatus as S


def test_every_status_has_entry():
    assert set(ALLOWED_TRANSITIONS) == set(S)


def test_allowed_transitions():
    assert ALLOWED_TRANSITIONS[S.PENDING] == {S.SUCCEEDED, S.FAILED}
    assert ALLOWED_TRANSITIONS[S.SUCCEEDED] == {S.REFUNDED}


def test_final_statuses_have_no_exits():
    assert ALLOWED_TRANSITIONS[S.FAILED] == set()
    assert ALLOWED_TRANSITIONS[S.REFUNDED] == set()