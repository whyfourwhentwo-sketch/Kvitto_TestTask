# Тестовое задание по FastAPI

## Быстрый запуск
```bash 
poetry install
poetry run uvicorn main:app --reload
```

## Тесты
```bash
poetry run pytest -q
```

## Сваггер
```text
http://127.0.0.1:8000/docs
```

##Примеры curl
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/tariffs' \
  -H 'accept: */*'
```
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/payments' \
  -H 'accept: */*' \
  -H 'idempotency-key: abc-126' \
  -H 'Content-Type: application/json' \
  -d '{
  "tariff_id": 1,
  "email": "user@example.com",
  "method": "installment",
  "installment_months": 3,
  "promo_code": "KVITTO10"
}'
```
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/payments/1' \
  -H 'accept: */*'
```