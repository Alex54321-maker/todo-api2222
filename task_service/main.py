import threading
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

# Автоматически добавляем корень проекта в пути, чтобы импортировать воркер
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

start_worker = None
print("🔍 [DEBUG] Пробуем импортировать worker.py...")

try:
    from worker import main as start_worker
    print("✅ [DEBUG] Воркер успешно импортирован из корня!")
except Exception as e:
    print(f"⚠️ [DEBUG] Ошибка первого импорта: {e}")
    try:
        from task_service.worker import main as start_worker
        print("✅ [DEBUG] Воркер успешно импортирован из task_service.worker!")
    except Exception as e2:
        print(f"❌ [DEBUG] Ошибка критического импорта воркера: {e2}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- КОД ПРИ СТАРТЕ ПРИЛОЖЕНИЯ ---
    print(f"🔍 [DEBUG] Статус start_worker перед запуском: {start_worker}")
    
    if start_worker:
        print("🧵 [DEBUG] Запуск фонового воркера RabbitMQ в параллельном потоке...")
        # Логируем также в наш лог-файл для истории
        logger.info("🧵 Запуск фонового воркера RabbitMQ в параллельном потоке...")
        
        worker_thread = threading.Thread(target=start_worker, daemon=True)
        worker_thread.start()
        
        print("✅ [DEBUG] Поток воркера запущен.")
        logger.info("✅ Поток воркера успешно инициализирован.")
    else:
        print("❌ [DEBUG] КРИТИЧЕСКАЯ ОШИБКА: start_worker равен None, поток не запущен!")
        logger.error("❌ Не удалось найти модуль worker.py для запуска фонового процесса!")
    
    yield  # Здесь приложение работает
    
    # --- КОД ПРИ ОСТАНОВКЕ ПРИЛОЖЕНИЯ ---
    logger.info("🛑 Накатываем завершение работы микросервиса задач...")

app = FastAPI(title="Task Microservice", version="1.0.0", lifespan=lifespan)

app.add_middleware(LoggingMiddleware)

Base.metadata.create_all(bind=engine)

@app.post("/tasks", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task_data: schemas.TaskCreate, db: Session = Depends(get_db)):
    new_task = models.Task(
        title=task_data.title,
        description=task_data.description,
        user_id=task_data.user_id,
        is_completed=False
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    logger.info(f"📋 Создана новая задача: ID #{new_task.id} для пользователя ID #{new_task.user_id}")
    
    try:
        send_task_created_event(task_id=new_task.id, user_id=new_task.user_id)
        logger.info(f"🚀 Событие отправлено в RabbitMQ для задачи #{new_task.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в RabbitMQ: {e}")
        
    return new_task

@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        logger.warning(f"🔍 Задача ID #{task_id} не найдена в базе данных")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task
