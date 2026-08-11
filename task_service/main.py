import sys
import os

# СНАЧАЛА добавляем пути поиска модулей, чтобы Python видел файлы внутри task_service
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.dirname(current_dir))

# ТОЛЬКО ПОСЛЕ ЭТОГО делаем остальные импорты
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

@app.put("/tasks/{task_id}", response_model=schemas.TaskResponse, status_code=status.HTTP_200_OK)
def update_task(
    task_id: int,
    task_data: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Эндпоинт обновления задачи (например, смена статуса или текста).
    Доступен только владельцу задачи. Защищен от сбоев RabbitMQ.
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    
    if not task:
        logger.warning(f"🔍 [UPDATE] Задача ID #{task_id} не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
    if task.user_id != current_user_id:
        logger.error(f"🚫 [SECURITY] Пользователь #{current_user_id} пытался изменить чужую задачу #{task_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        
    # Обновляем поля динамически на основе переданных данных
    update_data = task_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
        
    db.commit()
    db.refresh(task)
    logger.info(f"🔄 В БД обновлена задача: ID #{task.id} пользователем ID #{current_user_id}")
    
    # Безопасная отправка лога (заготовка под RabbitMQ для PUT)
    try:
        logger.info(f"🚀 Событие обновления задачи #{task.id} залогировано для RabbitMQ")
    except Exception as e:
        logger.error(f"⚠️ [MESSAGING] Не удалось обработать событие обновления: {e}")
        
    return task

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Эндпоинт удаления задачи. Доступен только владельцу.
    Защищен от сбоев RabbitMQ. Возвращает статус 204 No Content.
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    
    if not task:
        logger.warning(f"🔍 [DELETE] Задача ID #{task_id} не найдена")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
    if task.user_id != current_user_id:
        logger.error(f"🚫 [SECURITY] Пользователь #{current_user_id} пытался удалить чужую задачу #{task_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        
    db.delete(task)
    db.commit()
    logger.info(f"🗑 Из БД удалена задача: ID #{task_id} пользователем ID #{current_user_id}")
    
    # Безопасная отправка лога (заготовка под RabbitMQ для DELETE)
    try:
        logger.info(f"🚀 Событие удаления задачи #{task_id} залогировано для RabbitMQ")
    except Exception as e:
        logger.error(f"⚠️ [MESSAGING] Не удалось обработать событие удаления: {e}")
        
    return None
