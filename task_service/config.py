import os

class Settings:
    ENV: str = "development"
    SECRET_KEY: str = "9f8e4bc3a21d5e6f7b8a9c0d1e2f3a4b5c6d7e8f9a0b1c2d"

    # Параметры из твоего скриншота Neon.tech
    POSTGRES_DB: str = "neondb"
    POSTGRES_USER: str = "neondb_owner"
    POSTGRES_PASSWORD: str = "npg_5WHEZuVXg7if"
    POSTGRES_HOST: str = "ep-late-queen-a2vyhnhs-pooler.eu-central-1.aws.neon.tech"
    POSTGRES_PORT: str = "5432"

    # Параметры RabbitMQ для IDX (локальный докер-контейнер)
    RABBITMQ_DEFAULT_USER: str = "todo_rabbit_manager"
    RABBITMQ_DEFAULT_PASS: str = "zY4_vW9_mX2_kF7_pL1_sR5_tQ8_hB3"
    RABBITMQ_HOST: str = "127.0.0.1"
    RABBITMQ_PORT: str = "5672"

    def __init__(self):
        # Строка подключения с SSL, который требует Neon
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}?sslmode=require"
        self.RABBITMQ_URL = f"amqp://{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

settings = Settings()
