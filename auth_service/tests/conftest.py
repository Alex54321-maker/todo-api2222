import os
import pytest
from httpx import AsyncClient, ASGITransport

# Переменные для инициализации базы данных
os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5433/auth_db"
os.environ["JWT_SECRET"] = "super_secret_key_12345"

from main import app, Base, engine

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Автоматически создает и очищает таблицы для тестов."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def ac():
    """Фикстура асинхронного клиента FastAPI."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
