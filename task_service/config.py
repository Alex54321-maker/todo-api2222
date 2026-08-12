import os

class Settings:
    ENV: str = os.environ.get("ENV", "development")
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "temporary-secret-key-for-local-dev")

    # Чтение параметров базы данных из .env (с безопасными дефолтными значениями)
    POSTGRES_DB: str = os.environ.get("POSTGRES_DB", "postgres")
    POSTGRES_USER: str = os.environ.get("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    POSTGRES_PORT: str = os.environ.get("POSTGRES_PORT", "5432")

    # Чтение параметров RabbitMQ из .env
    RABBITMQ_DEFAULT_USER: str = os.environ.get("RABBITMQ_DEFAULT_USER", "guest")
    RABBITMQ_DEFAULT_PASS: str = os.environ.get("RABBITMQ_DEFAULT_PASS", "guest")
    RABBITMQ_HOST: str = os.environ.get("RABBITMQ_HOST", "127.0.0.1")
    RABBITMQ_PORT: str = os.environ.get("RABBITMQ_PORT", "5672")

    def __init__(self):
        # Строка подключения автоматически соберется из безопасных переменных
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode=require"
        self.RABBITMQ_URL = f"amqp://{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

settings = Settings()
