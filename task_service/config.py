from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Pydantic автоматически заберет DATABASE_URL из docker-compose
    DATABASE_URL: str
    
    # Добавляем чтение URL для RabbitMQ
    RABBITMQ_URL: str

    # Настройки для Pydantic v2
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Создаем глобальный объект настроек
settings = Settings()
