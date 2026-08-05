import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app
import os

# 1. Берём URL тестовой базы из окружения
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5433/test_tasks_db")

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Создаем таблицы перед началом всех тестов
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield
    # Опционально: можно дропать таблицы после тестов, если нужно очищать базу полностью
    # Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    # Создаем изолированную сессию для конкретного теста
    engine = create_engine(DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(autouse=True)
def override_dependencies(db_session):
    # Переопределяем зависимость get_db в FastAPI, чтобы эндпоинты шли в тестовую БД
    def _get_db_override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_rabbitmq():
    # Мокаем RabbitMQ, чтобы запросы не уходили в реальный брокер
    with patch("main.send_task_created_event") as mock_send:
        yield mock_send
