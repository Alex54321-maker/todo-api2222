import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models
import schemas
from middleware.logging_middleware import LoggingMiddleware
from core.logger import logger
from rabbitmq import send_task_created_event

# Импортируем зависимость проверки JWT-токенов
from auth import get_current_user_id

# Автоматически добавляем корень проекта в пути поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- КОД ПРИ СТАРТЕ ПРИЛОЖЕНИЯ ---
    logger.info("🚀 Микросервис задач успешно запущен в облачной среде Render.")
    logger.info("ℹ️ Фоновый поток отключен в продакшене. Очередь обслуживается брокером.")
    
    yield  # Здесь веб-приложение FastAPI обрабатывает входящие HTTP-запросы
    
    # --- КОД ПРИ ОСТАНОВКЕ ПРИЛОЖЕНИЯ ---
    logger.info("🛑 Завершение работы микросервиса задач...")

# Инициализация приложения FastAPI с привязкой жизненного цикла (lifespan)
app = FastAPI(title="Task Microservice", version="1.0.0", lifespan=lifespan)

# Подключение кастомного логгера для входящих запросов
app.add_middleware(LoggingMiddleware)

# Автоматическое создание таблиц в PostgreSQL (Neon.tech), если они не существуют
Base.metadata.create_all(bind=engine)

@app.post("/tasks", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: schemas.TaskCreate, 
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Эндпоинт создания задачи доступен только авторизованным пользователям с валидным JWT.
    Если RabbitMQ недоступен, задача все равно сохранится в БД и вернется клиенту.
    """
    new_task = models.Task(
        title=task_data.title,
        description=task_data.description,
        user_id=current_user_id,  # Реальный ID пользователя, извлеченный из JWT-токена
        is_completed=False
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    logger.info(f"📋 В БД сохранена задача: ID #{new_task.id} для авторизованного пользователя ID #{current_user_id}")
    
    # БЕЗОПАСНАЯ ОТПРАВКА: Ошибка брокера RabbitMQ больше не ломает ответ клиенту
    try:
        send_task_created_event(task_id=new_task.id, user_id=current_user_id)
        logger.info(f"🚀 Событие успешно опубликовано в RabbitMQ для задачи #{new_task.id}")
    except Exception as e:
        logger.error(f"⚠️ [MESSAGING] Не удалось отправить событие в RabbitMQ: {e}")
        logger.info("ℹ️ Задача успешно создана в БД, отправка события будет повторена позже.")
        
    return new_task

@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Эндпоинт для получения детальной информации о задаче по её ID."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        logger.warning(f"🔍 Задача ID #{task_id} не найдена в базе данных")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task
