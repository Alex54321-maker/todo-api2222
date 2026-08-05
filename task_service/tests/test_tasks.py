import pytest
from models import Task
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_and_get_task_in_db(db_session):
    new_task = Task(
        title="Купить молоко",
        description="Взять 2% жирности",
        is_completed=False,
        user_id=42
    )
    db_session.add(new_task)
    db_session.commit()
    db_session.refresh(new_task)
    
    assert new_task.id is not None
    assert new_task.title == "Купить молоко"
    assert new_task.user_id == 42
    assert new_task.is_completed is False

def test_create_task_endpoint(db_session, client, mock_rabbitmq):
    payload = {
        "title": "Тестовый таск через API",
        "description": "Описание эндпоинта",
        "user_id": 99
    }
    response = client.post("/tasks", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    
    # Проверяем, что интеграция с брокером сработала через мок
    mock_rabbitmq.assert_called_once()
    mock_rabbitmq.assert_called_with(task_id=data["id"], user_id=99)
    
    task_id = data["id"]
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Тестовый таск через API"

def test_get_task_not_found(db_session, client):
    non_existent_id = 99999
    response = client.get(f"/tasks/{non_existent_id}")
    
    assert response.status_code == 404
    assert "detail" in response.json()

@pytest.mark.parametrize("invalid_payload", [
    {"description": "Нет title и user_id"},
    {"title": "", "user_id": 99},
    {"title": "Валидный таск", "user_id": "not-an-integer"},
    {"title": "Валидный таск"}
])
def test_create_task_validation_error(db_session, client, invalid_payload):
    response = client.post("/tasks", json=invalid_payload)
    
    assert response.status_code == 422
    assert "detail" in response.json()
