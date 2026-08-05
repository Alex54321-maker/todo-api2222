from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import User
from schemas import UserCreate, UserResponse, UserLogin, Token
from security import get_password_hash, verify_password, create_access_token
from rabbitmq import publish_user_deleted_event

# 🔐 Импортируем созданные модули логирования
from middleware.logging_middleware import LoggingMiddleware
from core.logger import logger

app = FastAPI(title="Auth Microservice", version="1.0.0")

# 🚀 Подключаем автоматический перехват и логирование всех HTTP-запросов
app.add_middleware(LoggingMiddleware)

Base.metadata.create_all(bind=engine)

@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        logger.warning(f"⚠️ Попытка регистрации на уже существующий Email: {user_data.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"🆕 Создан новый пользователь: ID #{new_user.id} ({new_user.email})")
    return new_user

@app.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        logger.warning(f"🔒 Неудачная попытка входа для аккаунта: {login_data.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    
    logger.info(f"🔑 Успешный вход в систему: ID #{user.id} ({user.email}) -> Выдан JWT-токен")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/internal/users/{user_id}")
def check_user_exists(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"🔍 Внутренний запрос: Пользователь ID #{user_id} не найден в базе данных")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
        
    logger.debug(f"⚙️ Внутренний запрос: Статус пользователя ID #{user_id} подтвержден (Active)")
    return {"status": "active", "user_id": user_id}

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"🗑️ Попытка удаления несуществующего пользователя ID #{user_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    email_backup = user.email
    db.delete(user)
    db.commit()
    background_tasks.add_task(publish_user_deleted_event, user_id)
    
    logger.info(f"🗑️ Пользователь ID #{user_id} ({email_backup}) полностью удален. Событие отправлено в RabbitMQ.")
    return None
