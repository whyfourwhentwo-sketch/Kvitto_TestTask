import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models  # noqa: F401
from db import Base, get_db
from main import app


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