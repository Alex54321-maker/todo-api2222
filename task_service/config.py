from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    RABBITMQ_URL: str

    # Добавляем параметры для валидации JWT-токенов
    JWT_SECRET: str = "super-secret-key-for-local-dev-only"
    JWT_ALGORITHM: str = "HS256"

    # Настройки для Pydantic v2
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Создаем глобальный объект настроек
settings = Settings()
