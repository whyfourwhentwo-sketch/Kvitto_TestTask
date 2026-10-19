def body(**kw):
    return {"tariff_id": 1, "email": "a@b.com", "method": "card"} | kw


def create(client, headers=None, **kw):
    return client.post("/payments", json=body(**kw), headers=headers)


def hook(client, payment_id, status):
    return client.post("/webhooks/bank", json={"payment_id": payment_id, "status": status})


# --- tariffs ---

def test_list_tariffs(client):
    r = client.get("/tariffs")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert set(data[0]) == {"id", "title", "price"}


# --- create ---

def test_create_card_payment(client):
    r = create(client)
    assert r.status_code == 201
    p = r.json()
    assert p["status"] == "pending"
    assert p["amount"] == 100_000
    assert p["discount"] == 0
    assert p["schedule"] is None
    assert p["installment_months"] is None


def test_promo_is_case_insensitive(client):
    p = create(client, promo_code="SaLe10").json()
    assert p["amount"] == 90_000
    assert p["discount"] == 10_000


def test_invalid_promo_422(client):
    assert create(client, promo_code="wrong").status_code == 422


def test_installment_schedule(client):
    p = create(client, tariff_id=2, method="installment", installment_months=3).json()
    assert p["schedule"] == [83_334, 83_333, 83_333]
    assert sum(p["schedule"]) == p["amount"]


def test_installment_schedule_uses_discounted_amount(client):
    p = create(
        client, method="installment", installment_months=6, promo_code="sale10"
    ).json()
    assert sum(p["schedule"]) == 90_000


def test_installment_requires_months(client):
    assert create(client, method="installment").status_code == 422


def test_installment_rejects_wrong_months(client):
    assert create(client, method="installment", installment_months=5).status_code == 422


def test_months_not_allowed_for_card(client):
    assert create(client, method="card", installment_months=3).status_code == 422


def test_unknown_tariff_422(client):
    assert create(client, tariff_id=999).status_code == 422


def test_bad_email_422(client):
    assert create(client, email="not-an-email").status_code == 422


# --- idempotency ---

def test_idempotency_key_returns_same_payment(client):
    h = {"Idempotency-Key": "k1"}
    first = create(client, headers=h)
    second = create(client, headers=h)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_different_keys_create_different_payments(client):
    a = create(client, headers={"Idempotency-Key": "a"}).json()
    b = create(client, headers={"Idempotency-Key": "b"}).json()
    assert a["id"] != b["id"]


def test_no_key_always_creates_new(client):
    a = create(client)
    b = create(client)
    assert a.status_code == b.status_code == 201
    assert a.json()["id"] != b.json()["id"]


# --- get ---

def test_get_payment(client):
    pid = create(client).json()["id"]
    r = client.get(f"/payments/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid


def test_get_payment_404(client):
    assert client.get("/payments/9999").status_code == 404


# --- webhook ---

def test_webhook_success(client):
    pid = create(client).json()["id"]
    r = hook(client, pid, "succeeded")
    assert r.status_code == 200
    assert r.json() == {"result": "ok"}
    assert client.get(f"/payments/{pid}").json()["status"] == "succeeded"


def test_webhook_full_refund_flow(client):
    pid = create(client).json()["id"]
    assert hook(client, pid, "succeeded").status_code == 200
    assert hook(client, pid, "refunded").status_code == 200
    assert client.get(f"/payments/{pid}").json()["status"] == "refunded"


def test_webhook_payment_not_found(client):
    assert hook(client, 9999, "succeeded").status_code == 404


def test_webhook_invalid_transition(client):
    pid = create(client).json()["id"]
    r = hook(client, pid, "refunded")  # pending -> refunded запрещён
    assert r.status_code == 409
    assert r.json() == {"error": "invalid_transition"}
    assert client.get(f"/payments/{pid}").json()["status"] == "pending"


def test_webhook_same_status_is_conflict(client):
    pid = create(client).json()["id"]
    hook(client, pid, "succeeded")
    assert hook(client, pid, "succeeded").status_code == 409


def test_webhook_failed_is_final(client):
    pid = create(client).json()["id"]
    hook(client, pid, "failed")
    assert hook(client, pid, "succeeded").status_code == 409


def test_webhook_unknown_status_422(client):
    pid = create(client).json()["id"]
    assert hook(client, pid, "banana").status_code == 422