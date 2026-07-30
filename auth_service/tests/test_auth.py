import pytest
import asyncio
from unittest.mock import patch
from sqlalchemy.orm import Session
from main import get_db
from models import User
from security import get_password_hash

@pytest.mark.anyio
async def test_delete_user_triggers_background_task(ac):
    """
    Интеграционный тест:
    1. Создает пользователя напрямую в БД.
    2. Удаляет через роут DELETE /users/{id}.
    3. Проверяет вызов фоновой функции отправки события.
    """
    # 1. Готовим тестового пользователя в БД
    db_gen = get_db()
    db: Session = next(db_gen)
    
    test_user = User(email="test_delete@example.com", hashed_password=get_password_hash("password123"))
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    
    target_user_id = test_user.id
    db.close()

    # 2. Изолируем тест от сетевых хостов Docker через patch
    with patch("main.publish_user_deleted_event") as mock_publish:
        # Отправляем запрос на удаление
        response = await ac.delete(f"/users/{target_user_id}")
        assert response.status_code == 204

        # Даем микросекунду FastAPI на обработку BackgroundTasks
        await asyncio.sleep(0.1)

        # 3. Проверяем, что функция отправки в RabbitMQ вызвана с нужным ID
        mock_publish.assert_called_once_with(target_user_id)
