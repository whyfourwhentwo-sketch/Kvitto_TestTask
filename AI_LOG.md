# Лог чата: тестовое задание по FastAPI

Дата: 2026-10-19. Лог переписки с Claude при работе над тестовым заданием (платежи, тарифы, промокоды, рассрочка, вебхук банка). Стек: FastAPI, Pydantic v2, SQLAlchemy, SQLite, pytest + httpx, poetry.

---

## 1. Старт

**Пользователь:** Напишем тестовое задание по FastAPI?

**Claude:** Давай! Уточни, что именно нужно, чтобы я не гадал:

1. **Это ты пишешь тестовое** (для вакансии/стажировки), или хочешь, чтобы я составил задание для кого-то?
2. Если для себя, скинь текст задания: что нужно реализовать, какие требования к стеку (БД, авторизация, Docker, тесты и т.д.) и есть ли дедлайн.

Если задания пока нет и хочется просто потренироваться, могу предложить что-то типа мини-API на FastAPI: CRUD + SQLite/Postgres через SQLAlchemy, pydantic-схемы, пара тестов на pytest, Dockerfile. Скажи, в каком направлении идём.

---

## 2. Pydantic v2 и httpx

**Пользователь:** Давай сначала разберем зависимости в тз, я не до конца понимаю некоторые из них

pydantic v2, чем от первой отличается?
pytest + httpx, конкретно httpx что это и зачем?

**Claude:**

### Pydantic v2 vs v1

Pydantic валидирует данные и описывает схемы запросов/ответов в FastAPI. Главное в v2:

- Ядро переписано на Rust, так что валидация в разы быстрее.
- Поменялся API, часть методов переименована.

```python
# v1
class User(BaseModel):
    name: str
    age: Optional[int]          # в v1 это необязательное поле

    @validator("name")
    def check_name(cls, v): ...

    class Config:
        orm_mode = True

user.dict()
user.json()
User.parse_obj(data)

# v2
class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    age: int | None = None      # в v2 без "= None" поле обязательное!

    @field_validator("name")
    @classmethod
    def check_name(cls, v): ...

user.model_dump()
user.model_dump_json()
User.model_validate(data)
```

Ещё `BaseSettings` (для конфигов из `.env`) переехал в отдельный пакет `pydantic-settings`. Если в ТЗ написано v2, значит, пиши в новом стиле и не копируй старые ответы со StackOverflow с `.dict()` и `orm_mode`.

### httpx

Это HTTP-клиент, как `requests`, только с поддержкой async. В тестах FastAPI он нужен, потому что `TestClient` под капотом работает на httpx. Без него в окружении тест просто не запустится.

Синхронный тест:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
```

Если эндпоинты и работа с БД async, обычно берут `AsyncClient` напрямую (плюс `pytest-asyncio` или `anyio`):

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
```

Сервер при этом поднимать не надо: запросы идут прямо в приложение в памяти.

Установка:

```bash
pip install "pydantic>=2" pytest httpx
```

---

## 3. Установка зависимостей через poetry

**Пользователь:** пока окей,
Я настроил poetry, нужно поставить все необходимое. + sqlalchemy

**Claude:** Ставим всё одной командой:

```bash
poetry add fastapi "uvicorn[standard]" "pydantic>=2" sqlalchemy
poetry add --group dev pytest httpx
```

Тестовые зависимости (pytest, httpx) кладём в dev-группу, чтобы они не попадали в прод-образ.

Что ещё добавить, зависит от БД и от того, sync у тебя или async:

```bash
# Postgres, async (asyncpg)
poetry add asyncpg
# Postgres, sync
poetry add "psycopg[binary]"
# SQLite async
poetry add aiosqlite
# SQLite sync: ничего не нужно, драйвер встроен в Python

# если нужны конфиги из .env
poetry add pydantic-settings

# если используешь async-тесты
poetry add --group dev pytest-asyncio

# миграции (часто просят в ТЗ)
poetry add alembic
```

Проверить, что встало:

```bash
poetry show --tree
```

Запуск: `poetry run uvicorn app.main:app --reload`

---

## 4. Выбор БД: SQLite

**Пользователь:** БД думаю SQLite, но до этого работал только с постгрес, сейчас просто ставить долго

**Claude:** SQLite для тестового нормальный выбор: ничего поднимать не надо, файл БД лежит в проекте, а проверяющему проще запустить. Если в ТЗ явно не требуют Postgres, бери его.

Драйвер ставить не нужно, он встроен в Python. Если хочешь async, добавь `aiosqlite`:

```bash
poetry add aiosqlite   # только для async
```

Строка подключения:

```python
# sync
engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})

# async
engine = create_async_engine("sqlite+aiosqlite:///./app.db")
```

`check_same_thread=False` нужен в sync-варианте, потому что FastAPI гоняет запросы по разным потокам, а SQLite по умолчанию это запрещает.

Отличия от Postgres, на которые можно напороться:

- Типы нестрогие: SQLite не будет ругаться, если положить строку в integer-колонку. Валидацию держи на pydantic.
- Внешние ключи по умолчанию выключены, включаются через `PRAGMA foreign_keys=ON`.
- Нет настоящих `ENUM`, `ARRAY`, `JSONB`. Простой `JSON` в SQLAlchemy работает.
- `ALTER TABLE` ограничен, поэтому с alembic нужен `render_as_batch=True`.
- Запись блокирует всю БД, но для тестового это не проблема.

Для тестов удобно брать `sqlite:///:memory:` или отдельный файл, чтобы не трогать основную БД.

Если в коде ничего не завязано на специфику Postgres, переезд потом сводится к замене строки подключения и драйвера.

---

## 5. SQLite встроена?

**Пользователь:** Не понял, sqlite сразу встроена или что?

**Claude:** Да, сразу встроена. В стандартной библиотеке Python есть модуль `sqlite3`, и SQLAlchemy через него и работает. Ставить ничего не надо.

Проверить можно так:

```bash
poetry run python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

Если вывелась версия, всё на месте.

В отличие от Postgres, здесь нет отдельного сервера: БД это просто файл (`app.db`), который создастся сам при первом подключении. Поэтому и нет долгой установки.

`aiosqlite` нужен только для async. Это обёртка поверх того же `sqlite3`, чтобы запросы не блокировали event loop.

---

## 6. Архитектура: бизнес-правила

**Пользователь:** окей, тогда пошли по архитектуре.

Пока без кода, разберем структуру модулей.

Ситуация следующая:
Есть хардкод тарифов + промокод
basic, standart, premium все суммы в копейках воизбежание ошибок с плавающей точкой
Промокод на -10% к тарифу, регистр не важен, ошибка вернет 422 (неверный код)

Способ оплаты: card, sbp, installment, рассрочка допом требует срок 3, 6, 12 месяцев

Рассрочка: сумма платежа делиться ровно на месяцы, дроби округляем в нижнюю сторону, недостающие копейки кидаем в первые платежи.

Статусы: Новый платеж - pending, доступные переходы pending - succeeded, pending - failed, succeeded - refunded

дополнение в процессе написания этого - стоит ли включать redis для более мощной обертки вокруг статусов платежей или лучше будет просто симулировать это?

**Claude:**

### Redis

Не нужен, симулировать тоже ничего не надо. Статусы платежа это маленький конечный автомат: таблица разрешённых переходов (`pending -> succeeded/failed`, `succeeded -> refunded`) и проверка перед сменой статуса. Для защиты от гонок (два одновременных запроса на один платёж) хватает транзакции в БД. Redis имеет смысл для распределённых блокировок, очередей и кэша, а у тебя один сервис и SQLite. Если захочется показать, что ты про это думал, напиши пару строк в README про то, что бы ты делал в проде.

### Структура

```
app/
├── main.py            # создание приложения, подключение роутеров, обработчики ошибок
├── db.py              # engine, сессия, Base
├── models.py          # SQLAlchemy: Payment (+ Installment, если хранишь график)
├── schemas.py         # pydantic: запросы и ответы
├── tariffs.py         # хардкод: тарифы, промокоды (данные, без логики)
├── pricing.py         # чистые функции: цена тарифа + промокод
├── installments.py    # чистая функция: сумма + срок -> список платежей
├── status.py          # enum статусов + таблица допустимых переходов
├── service.py         # сценарии: создать платёж, сменить статус
└── api.py             # эндпоинты, тонкие: принял -> service -> вернул
tests/
├── test_pricing.py
├── test_installments.py
├── test_status.py
└── test_api.py
```

Слои делить глубже (repository, unit of work и так далее) не стоит, для такого объёма это перебор. `pricing`, `installments` и `status` не знают ни про БД, ни про FastAPI, поэтому тестируются обычными юнит-тестами.

### Моменты, где обычно ошибаются

- **Рассрочка.** `base = total // n`, `rem = total % n`, первым `rem` платежам добавляется по 1 копейке. Пример: 1000 коп. на 3 месяца дают 334, 333, 333. Сумма платежей всегда должна равняться `total`, это хорошее свойство для теста.
- **Скидка 10%.** В копейках она тоже может дать дробь, например 10% от 9999. Нужно решить, как округлять, и зафиксировать это. Считай целыми: `price * 90 // 100`, а не `price * 0.9`. Если в ТЗ про округление ничего нет, выбери вниз или вверх и напиши в README.
- **Валидация способа оплаты.** Правило «`installment` требует `months` из {3, 6, 12}, а для card и sbp `months` должен быть пустым» удобно делать через `model_validator` в pydantic, и 422 вернётся сам.
- **Неверный промокод.** Для него нужен свой 422, который ты вернёшь из сервиса. Регистр нормализуй один раз на входе (`.strip().lower()`).
- **Недопустимый переход статуса.** В ТЗ код ошибки не указан. Обычно это 409 Conflict, но проверь, не прописано ли что-то своё. Повторный переход в тот же статус (например `succeeded -> succeeded`) тоже решить заранее: ошибка или идемпотентный ответ.
- **Сумма в БД.** Храни в `Integer` в копейках. Скидку и итоговую цену лучше сохранять в платеже, чтобы они не пересчитывались, если тарифы потом поменяются.

---

## 7. Архитектура: эндпоинты из ТЗ

**Пользователь:**

> GET /tariffs 200 — список тарифов [{ id, title, price }] .
> POST /payments Тело: tariff_id , email , method , installment_months (для рассрочки), promo_code (необязательно). 201 — платёж создан. Если передан заголовок Idempotency-Key и платёж с таким ключом уже есть — вернуть его же с кодом 200, второй не создавать.
> GET /payments/{id} 200 — платёж; 404, если его нет.
> POST /webhooks/bank Банк сообщает о смене статуса. Тело: payment_id , status . Платежа нет — 404. Запрещённый переход — 409 { error: "invalid_transition" } , статус не меняется. Успех — 200 { result: "ok" } .
> Платёж в ответах: id , status , tariff_id , amount , discount , method , installment_months , schedule — список сумм в копейках или null , email , created_at .
> Ошибки валидации — стандартный ответ FastAPI с кодом 422, свой формат не нужен

**Claude:**

### Структура под эти эндпоинты

```
app/
├── main.py            # приложение, роутеры, маппинг доменных ошибок -> HTTP
├── db.py
├── models.py          # одна таблица Payment
├── schemas.py         # PaymentCreate, PaymentOut, TariffOut, WebhookIn
├── tariffs.py         # хардкод тарифов и промокодов
├── pricing.py         # цена + промокод -> (amount, discount)
├── installments.py    # сумма + месяцы -> schedule
├── status.py          # enum + таблица переходов
├── errors.py          # доменные исключения
├── service.py         # create_payment, get_payment, apply_webhook
└── routers/
    ├── tariffs.py     # GET /tariffs
    ├── payments.py    # POST /payments, GET /payments/{id}
    └── webhooks.py    # POST /webhooks/bank
```

Таблица `Installment` не нужна. `schedule` детерминированно считается из `amount` и `installment_months`, поэтому в БД хватает `installment_months` (nullable), а график строится при формировании ответа.

### Что важно по эндпоинтам

**Idempotency-Key**
- Колонка `idempotency_key` в `Payment`: nullable, с `UNIQUE`.
- Алгоритм: если ключ пришёл, ищем платёж с таким ключом. Нашли - возвращаем его с 200. Нет - создаём с 201.
- Два одновременных запроса с одним ключом пройдут проверку «нет такого» оба. Поэтому `UNIQUE` нужен как страховка: ловишь `IntegrityError` и отдаёшь уже существующий платёж. Это то, на что обычно смотрят в ревью.
- Если тот же ключ пришёл с другим телом, в ТЗ ничего нет. Проще всего просто вернуть старый платёж, и это можно упомянуть в README.
- Без заголовка идемпотентности нет, каждый запрос создаёт новый платёж.

**Формат ошибок**
- `HTTPException(detail=...)` вернёт `{"detail": ...}`, а для webhook нужен ровно `{"error": "invalid_transition"}`.
- Решение: сервис бросает свои исключения из `errors.py` (`InvalidTransition`, `PaymentNotFound`, `InvalidPromo`). В `main.py` для них навешиваются `exception_handler`, которые возвращают нужный JSON. Сервис при этом не знает про FastAPI.
- Успешный ответ вебхука `{result: "ok"}` лучше сделать отдельной маленькой схемой.
- Неверный промокод это 422. Для него подходит стандартный `{"detail": ...}`, свой формат не нужен.

**POST /payments, валидация**
- `model_validator` на `PaymentCreate`: для `installment` нужен `installment_months` из {3, 6, 12}, для `card` и `sbp` его быть не должно. Тогда 422 приходит автоматически.
- `email` через `EmailStr` требует пакет: `poetry add email-validator`. Без него приложение упадёт на импорте.
- `promo_code` нормализуй (`strip().lower()`) до сравнения.
- Неизвестный `tariff_id`: в ТЗ не сказано, что возвращать. Я бы выбрал 422, потому что это некорректное значение в теле. Но можно и 404. Выбери одно и запиши в README.

**POST /webhooks/bank**
- `status` в `WebhookIn` объяви как enum. Тогда мусорное значение даст 422 само.
- Порядок проверок: платёж есть? (404), затем переход допустим? (409). При 409 статус не меняется, это делается проверкой до записи.
- Повторная доставка того же статуса (`succeeded -> succeeded`) по твоей таблице будет 409. Банки часто ретраят вебхуки, так что имей это в виду. Если в ТЗ про повтор ничего нет, придерживайся таблицы строго.
- Смену статуса делай в одной транзакции: прочитал, проверил, записал.

**PaymentOut**
- `amount` и `discount` в ТЗ не расшифрованы. Я бы считал `amount` итоговой суммой к оплате (после скидки), а `discount` размером скидки в копейках. Сумма платежей в `schedule` должна равняться именно `amount`. Если в ТЗ есть формулировка точнее, ориентируйся на неё.
- Если скидки нет, `discount` равен 0, а не null.
- `created_at` ставь на сервере в UTC.
- `schedule` равен `null` для card и sbp.

---

## 8. tariff_id через enum

**Пользователь:** tariff_id, как мне кажется, можно через enum определить. Во-первых это будет уникальным значением, в enum не получится два одинаковых значения забить. Но enum так или иначе просто число, это только читаемость повысит.

Итогом id парсится как число на фронте (представим, что фронт есть), по тому же перечислению, что и на бэке.

**Claude:** Идея рабочая, но в рассуждении есть неточности.

**Что верно.** Если сделать `tariff_id: TariffId` в `PaymentCreate`, pydantic сам вернёт 422 на неизвестный id. Это закрывает вопрос, что отдавать при несуществующем тарифе, и отдельной проверки в сервисе не нужно.

**Что поправить:**

- **Enum не равно число.** Обычный `Enum` с числовыми значениями числом не является, а в JSON он не сериализуется как число. Нужен `IntEnum`. Если в ТЗ id это строка вроде `"basic"`, тогда `class TariffId(str, Enum)`, и читаемость будет ещё лучше. Проверь, какой тип у `id` в ТЗ.
- **Уникальность не гарантирована.** Два одинаковых имени Python не даст, а два одинаковых значения молча превратятся в алиас. Чтобы получить ошибку, ставь декоратор `@unique`.
- **Фронт не делит enum с бэком.** Python-класс до фронта не доезжает. Источник правды для фронта это `GET /tariffs`, он как раз отдаёт `{id, title, price}`. Если фронт будет зашивать у себя копию перечисления, получится дублирование, которое разъедется при первом изменении. Для тестового достаточно, чтобы фронт брал список из эндпоинта.

**Как это уложить в структуру.** В `tariffs.py` лежат `TariffId` и один словарь `TARIFFS: dict[TariffId, Tariff]` с title и price. Больше ничего не нужно: ни классов-репозиториев, ни отдельной таблицы в БД. В тесты добавь простую проверку, что для каждого члена enum есть запись в словаре, чтобы при добавлении нового тарифа не забыть вторую половину.

В `Payment` храни `tariff_id` как обычный `Integer` (или строку). Привязывать колонку к enum на уровне БД смысла нет: в SQLite это всё равно не работает по-настоящему.

---

## 9. Начало реализации: константы, БД, модель, схемы

**Пользователь:** Тогда давай начнем. По порядку с утилит - пидантик схемы, база данных, различные конфиг файлы с константами

**Claude:** Начинаем с зависимости, которой не хватает:

```bash
poetry add email-validator
```

Дальше файлы в порядке зависимости: константы, БД, модель, схемы. Я взял sync SQLAlchemy, чтобы не усложнять: для SQLite и тестового задания async ничего не даёт.

### `app/config.py`

```python
DATABASE_URL = "sqlite:///./app.db"
INSTALLMENT_MONTHS = (3, 6, 12)
```

### `app/enums.py`

```python
from enum import Enum


class PaymentMethod(str, Enum):
    CARD = "card"
    SBP = "sbp"
    INSTALLMENT = "installment"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


ALLOWED_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.PENDING: {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED},
    PaymentStatus.SUCCEEDED: {PaymentStatus.REFUNDED},
    PaymentStatus.FAILED: set(),
    PaymentStatus.REFUNDED: set(),
}
```

Таблица переходов лежит рядом с enum как данные. Сама проверка перехода будет в сервисе.

### `app/tariffs.py` (первая версия, см. упрощение в разделе 10)

```python
from dataclasses import dataclass
from enum import IntEnum, unique


@unique
class TariffId(IntEnum):
    BASIC = 1
    STANDARD = 2
    PREMIUM = 3


@dataclass(frozen=True)
class Tariff:
    id: TariffId
    title: str
    price: int  # копейки


TARIFFS: dict[TariffId, Tariff] = {
    t.id: t
    for t in (
        Tariff(TariffId.BASIC, "Basic", 100_000),
        Tariff(TariffId.STANDARD, "Standard", 250_000),
        Tariff(TariffId.PREMIUM, "Premium", 500_000),
    )
}

# код в нижнем регистре -> скидка в процентах
PROMO_CODES: dict[str, int] = {"sale10": 10}
```

Цены, id, названия и сам промокод тут заглушки. Подставь значения из ТЗ.

### `app/db.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db
```

### `app/models.py`

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import PaymentMethod, PaymentStatus


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
```

Поля `schedule` в модели нет: график считается из `amount` и `installment_months`. SQLite не хранит таймзону, поэтому `created_at` после чтения из БД придёт без неё. Если в ТЗ это важно, нормализуем на выходе.

### `app/schemas.py`

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.config import INSTALLMENT_MONTHS
from app.enums import PaymentMethod, PaymentStatus
from app.tariffs import TariffId


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
```

Что тут важно:

- `schedule` с дефолтом `None` нужен, чтобы `from_attributes` не падал на отсутствующем атрибуте модели. Значение подставим, когда напишем `installments.py`.
- Неизвестный `tariff_id` и мусорный `status` в вебхуке отсекаются самим pydantic, это 422 без дополнительного кода.
- Пустая строка в `promo_code` останется `""` и позже попадёт под «неверный промокод».

Таблицы создаём в `main.py` через `Base.metadata.create_all(engine)`, до этого дойдём вместе с приложением.

---

## 10. Упрощение `Tariff`

**Пользователь:**

```python
TARIFFS: dict[TariffId, Tariff] = {
    t.id: t
    for t in (
        Tariff(TariffId.BASIC, "Basic", 100_000),
        Tariff(TariffId.STANDARD, "Standard", 250_000),
        Tariff(TariffId.PREMIUM, "Premium", 500_000),
    )
}
```

Я не до конца понимаю, что ты хотел тут добиться. Почему нельзя просто перечислить. Зачем в классе тарифа айди, если он по итогу есть в словаре?

**Claude:** Ты прав, это лишнее усложнение. Я хотел, чтобы у `Tariff` был свой `id`, и он удобно превращался бы в `TariffOut` целиком, а словарь по id нужен для быстрого поиска при создании платежа. В итоге id хранится в двух местах (ключ и поле), и их можно рассинхронизировать. Выигрыш при этом копеечный.

Проще так:

```python
@dataclass(frozen=True)
class Tariff:
    title: str
    price: int  # копейки


TARIFFS: dict[TariffId, Tariff] = {
    TariffId.BASIC: Tariff("Basic", 100_000),
    TariffId.STANDARD: Tariff("Standard", 250_000),
    TariffId.PREMIUM: Tariff("Premium", 500_000),
}
```

id живёт только как ключ. Для `GET /tariffs` собираешь ответ на лету:

```python
[TariffOut(id=tid, title=t.title, price=t.price) for tid, t in TARIFFS.items()]
```

А при создании платежа берёшь `TARIFFS[payload.tariff_id]`. Ничего другого не нужно.

Проверка в тестах, что для каждого члена `TariffId` есть запись в `TARIFFS`, остаётся актуальной.

---

## 11. Остальное: ошибки, рассрочка, сервис, эндпоинты, main

**Пользователь:** Давай остальное: эндпоинты, ошибки, подсчет рассрочки, и main.

**Claude:** Всё сводится к таким файлам. Роутеры я свёл в один `api.py`, три эндпоинта на три файла это перебор.

```
app/
├── __init__.py       # пустой, если ещё нет
├── errors.py
├── pricing.py
├── installments.py
├── service.py
├── api.py
└── main.py
```

### `app/errors.py`

```python
class PaymentNotFound(Exception): ...
class InvalidPromo(Exception): ...
class InvalidTransition(Exception): ...
```

### `app/pricing.py`

```python
from app.errors import InvalidPromo
from app.tariffs import PROMO_CODES


def calculate(price: int, promo_code: str | None) -> tuple[int, int]:
    """Возвращает (amount, discount) в копейках."""
    if promo_code is None:
        return price, 0
    percent = PROMO_CODES.get(promo_code)
    if percent is None:
        raise InvalidPromo
    discount = price * percent // 100  # только целые, без float
    return price - discount, discount
```

Скидка округляется вниз, то есть лишняя копейка остаётся с клиента. Если в ТЗ про это ничего нет, напиши выбор в README.

### `app/installments.py`

```python
def build_schedule(amount: int, months: int) -> list[int]:
    base, rem = divmod(amount, months)
    return [base + 1 if i < rem else base for i in range(months)]
```

Пример: `build_schedule(1000, 3)` даёт `[334, 333, 333]`. Так как `rem < months`, каждому из первых платежей достаётся максимум одна копейка.

### `app/service.py`

```python
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.enums import ALLOWED_TRANSITIONS, PaymentStatus
from app.errors import InvalidTransition, PaymentNotFound
from app.installments import build_schedule
from app.models import Payment
from app.pricing import calculate
from app.schemas import PaymentCreate, PaymentOut
from app.tariffs import TARIFFS


def _by_key(db: Session, key: str) -> Payment | None:
    return db.scalar(select(Payment).where(Payment.idempotency_key == key))


def create_payment(db: Session, data: PaymentCreate, key: str | None) -> tuple[Payment, bool]:
    """Возвращает (платёж, создан_ли_новый)."""
    if key and (existing := _by_key(db, key)):
        return existing, False

    amount, discount = calculate(TARIFFS[data.tariff_id].price, data.promo_code)
    payment = Payment(
        idempotency_key=key,
        tariff_id=data.tariff_id,
        email=data.email,
        method=data.method,
        installment_months=data.installment_months,
        amount=amount,
        discount=discount,
    )
    db.add(payment)
    try:
        db.commit()
    except IntegrityError:
        # параллельный запрос с тем же ключом успел раньше
        db.rollback()
        existing = _by_key(db, key) if key else None
        if existing is None:
            raise
        return existing, False
    return payment, True


def get_payment(db: Session, payment_id: int) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise PaymentNotFound
    return payment


def apply_webhook(db: Session, payment_id: int, new_status: PaymentStatus) -> None:
    payment = get_payment(db, payment_id)
    if new_status not in ALLOWED_TRANSITIONS[payment.status]:
        raise InvalidTransition
    payment.status = new_status
    db.commit()


def to_out(payment: Payment) -> PaymentOut:
    out = PaymentOut.model_validate(payment)
    if payment.installment_months:
        out.schedule = build_schedule(payment.amount, payment.installment_months)
    return out
```

### `app/api.py`

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app import service
from app.db import get_db
from app.schemas import PaymentCreate, PaymentOut, TariffOut, WebhookIn, WebhookOut
from app.tariffs import TARIFFS

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


@router.get("/tariffs", response_model=list[TariffOut])
def list_tariffs():
    return [TariffOut(id=tid, title=t.title, price=t.price) for tid, t in TARIFFS.items()]


@router.post("/payments", response_model=PaymentOut, status_code=201)
def create_payment(
    payload: PaymentCreate,
    response: Response,
    db: DB,
    idempotency_key: Annotated[str | None, Header()] = None,
):
    payment, created = service.create_payment(db, payload, idempotency_key)
    if not created:
        response.status_code = 200
    return service.to_out(payment)


@router.get("/payments/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: DB):
    return service.to_out(service.get_payment(db, payment_id))


@router.post("/webhooks/bank", response_model=WebhookOut)
def bank_webhook(payload: WebhookIn, db: DB):
    service.apply_webhook(db, payload.payment_id, payload.status)
    return WebhookOut()
```

FastAPI превращает `idempotency_key` в заголовок `Idempotency-Key` сам.

### `app/main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (чтобы Payment попал в metadata)
from app.api import router
from app.db import Base, engine
from app.errors import InvalidPromo, InvalidTransition, PaymentNotFound


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.exception_handler(PaymentNotFound)
async def payment_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "payment not found"})


@app.exception_handler(InvalidPromo)
async def invalid_promo(request, exc):
    return JSONResponse(status_code=422, content={"detail": "invalid promo code"})


@app.exception_handler(InvalidTransition)
async def invalid_transition(request, exc):
    return JSONResponse(status_code=409, content={"error": "invalid_transition"})
```

### Проверка руками

```bash
poetry run uvicorn app.main:app --reload
```

```bash
curl -X POST localhost:8000/payments \
  -H "Content-Type: application/json" -H "Idempotency-Key: abc1" \
  -d '{"tariff_id":2,"email":"a@b.com","method":"installment","installment_months":3,"promo_code":"SALE10"}'
```

Второй такой же запрос должен вернуть тот же платёж, но уже с кодом 200. Swagger лежит на `localhost:8000/docs`.

### На что обратить внимание

- **Гонка в вебхуках.** `apply_webhook` читает статус, проверяет, потом пишет. Два одновременных вебхука на один платёж теоретически могут оба увидеть `pending`. Для тестового нормально, но в README можно написать, что в проде это решается условным `UPDATE ... WHERE status = :old` или блокировкой строки.
- **Ключ с другим телом.** Сейчас просто вернётся старый платёж без проверки совпадения тела.
- **Формат 404 и неверного промокода.** В ТЗ он не задан, поэтому я сделал `{"detail": "..."}` как в стандартном ответе FastAPI.

---

## 12. Как работают обработчики исключений

**Пользователь:** обработчики исключений в мейне почему кидают json вместо http? или статус код все равно автоматом подтянется?

**Claude:** Статус-код подтягивается не автоматически, а потому что мы его явно указали в `status_code=...`. А JSON и HTTP тут не противопоставляются: HTTP-ответ состоит из статуса, заголовков и тела, и JSON это тело. `JSONResponse(status_code=409, content={...})` возвращает полноценный HTTP-ответ с кодом 409 и JSON в теле.

Если убрать `status_code`, ответ уйдёт с кодом 200 по умолчанию, хотя в теле будет ошибка. Это частая ловушка.

Посмотреть самому можно через `curl -i` (показывает статус-строку и заголовки):

```bash
curl -i localhost:8000/payments/9999
```

```
HTTP/1.1 404 Not Found
content-type: application/json

{"detail":"payment not found"}
```

Зачем вообще нужны свои обработчики, если есть `HTTPException`. Он делает то же самое внутри: у FastAPI есть встроенный обработчик, который превращает его в `JSONResponse(status_code=..., content={"detail": ...})`. Но тело всегда будет `{"detail": ...}`, а для вебхука в ТЗ нужен ровно `{"error": "invalid_transition"}`. Свой `exception_handler` даёт тот же механизм с произвольным телом, и заодно сервис не знает про HTTP: он бросает `InvalidTransition`, а в какой код это превратится, решает `main.py`.

---

## 13. Тесты

**Пользователь:** Давай тесты допишем и я сяду разбираться в этом.

**Claude:** Тесты синхронные, так что ни `pytest-asyncio`, ни `AsyncClient` не нужны, хватит `TestClient`.

```
tests/
├── conftest.py
├── test_pricing.py
├── test_installments.py
├── test_status.py
└── test_api.py
```

### `pyproject.toml`

Чтобы `import app` работал из тестов, добавь:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

### `tests/conftest.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.db import Base, get_db
from app.main import app


@pytest.fixture
def client():
    # in-memory БД, новая на каждый тест
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # одно соединение, иначе in-memory БД у каждого своя
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)  # без `with`, значит lifespan не запускается и app.db не создаётся
    app.dependency_overrides.clear()
    engine.dispose()
```

### `tests/test_pricing.py`

```python
import pytest

from app.errors import InvalidPromo
from app.pricing import calculate
from app.tariffs import TARIFFS, TariffId


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
```

### `tests/test_installments.py`

```python
import pytest

from app.installments import build_schedule


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
```

### `tests/test_status.py`

```python
from app.enums import ALLOWED_TRANSITIONS, PaymentStatus as S


def test_every_status_has_entry():
    assert set(ALLOWED_TRANSITIONS) == set(S)


def test_allowed_transitions():
    assert ALLOWED_TRANSITIONS[S.PENDING] == {S.SUCCEEDED, S.FAILED}
    assert ALLOWED_TRANSITIONS[S.SUCCEEDED] == {S.REFUNDED}


def test_final_statuses_have_no_exits():
    assert ALLOWED_TRANSITIONS[S.FAILED] == set()
    assert ALLOWED_TRANSITIONS[S.REFUNDED] == set()
```

### `tests/test_api.py`

```python
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
```

### Запуск

```bash
poetry run pytest -q
poetry run pytest tests/test_api.py -k webhook -v   # только вебхуки
```

Что может пойти не так при первом прогоне:

- **`ModuleNotFoundError: app`**: не добавил `pythonpath` в `pyproject.toml`, либо нет `app/__init__.py`.
- **Цифры в тестах завязаны на заглушки из `tariffs.py`**: 100_000 для тарифа 1, 250_000 для тарифа 2 и промокод `sale10`. Если подставил значения из ТЗ, поправь числа в `test_api.py` и `test_pricing.py`.
- **`[0]` в `build_schedule(2, 3) == [1, 1, 0]`**: нулевой платёж на практике странный, но ТЗ такое не запрещает. Если захочешь это запретить, получится новое правило валидации.

Параллельную гонку с одинаковым `Idempotency-Key` эти тесты не ловят, ветка с `IntegrityError` в `service.py` останется непокрытой. Для тестового это ок, но в README можно упомянуть.

Если какой-то тест упадёт или что-то в коде окажется непонятным, кидай сюда, разберём.

---

## 14. Точность хранения суммы

**Пользователь:** имеет ли смысл увеличить хранимую валюту с копеек до копеек * 10, чтобы потери округления были микроскопическими?

**Claude:** Нет, это усложнение без пользы, и к тому же оно ломает ТЗ: там суммы в копейках, и фронт с банком ждут именно их.

**Потерь при округлении у тебя и так нет.** Есть два места, где появляется дробь:

- **Рассрочка.** Остаток раскидывается по первым платежам, и сумма графика всегда равна `amount` ровно. Ни одна копейка не пропадает, это покрыто тестом `sum(s) == amount`.
- **Скидка.** Тут округление реально происходит (10% от 9999 это 999,9 коп. и мы берём 999). Но это не потеря, а решение «какой будет итоговая цена». Клиент всё равно платит целое число копеек, потому что дробной копейки не существует.

**Почему «копейки × 10» не помогает.** Округление не исчезнет, оно просто переедет в момент, когда ты переводишь внутреннюю сумму в то, что реально можно списать с карты. Там снова придётся решать, вниз или вверх. К тому же хранить 99,99 как 99990 значит добавить скрытый множитель, который легко забыть в одном из мест, и получить ошибку в 10 раз.

Дробные доли минимальной единицы нужны там, где они реально есть: цена за токен или за единицу товара с долями цента, валютные курсы, крипта. Тогда берут `Decimal` или более мелкую единицу, но для этого есть бизнес-причина. Здесь её нет: тариф стоит целое число копеек, скидка 10% даёт максимум 0,9 копейки погрешности на платёж.

Достаточно, чтобы в README одной строкой было записано правило округления скидки («вниз, целочисленно»). Для проверяющего это важнее, чем лишний порядок точности.

---

## Итоговые решения (для README)

- БД: SQLite, sync SQLAlchemy 2.0, таблица `payments`, график рассрочки не хранится, а считается из `amount` и `installment_months`.
- Суммы: целые копейки везде; скидка считается целочисленно и округляется вниз.
- Рассрочка: сумма делится поровну, остаток по одной копейке добавляется первым платежам.
- `tariff_id`: `IntEnum` с `@unique`, неизвестный id даёт стандартный 422.
- Неверный промокод: 422 `{"detail": "invalid promo code"}`, регистр не важен.
- Идемпотентность: заголовок `Idempotency-Key`, колонка с `UNIQUE`, при гонке ловится `IntegrityError`; тот же ключ с другим телом возвращает старый платёж.
- Статусы: таблица переходов `pending -> succeeded|failed`, `succeeded -> refunded`; всё остальное, включая повтор того же статуса, даёт 409 `{"error": "invalid_transition"}`.
- Redis не используется; в проде гонки на вебхуках решались бы условным `UPDATE ... WHERE status = :old` или блокировкой строки.
