import time
import json
import pika
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Импортируем централизованные настройки и логгер твоего проекта
try:
    from config import settings
    from core.logger import logger
except ImportError:
    # Резервный импорт на случай запуска скрипта напрямую вне контекста пакета
    settings = None
    import logging
    logger = logging.getLogger(__name__)

# Настройки SMTP для работы внутри Docker-сети с контейнером test_mail (Mailpit)
SMTP_SERVER = os.getenv("SMTP_SERVER", "test_mail")
SMTP_PORT = int(os.getenv("SMTP_PORT", 1025))
SMTP_USER = os.getenv("SMTP_USER", "wormsbecher.alexander@gmail.com")

# Резервный хост RabbitMQ для локального Docker
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "microservices_rabbitmq")

def send_email_notification(task_id, user_id, status):
    """Функция для отправки Email через SMTP Mailpit внутри Docker или внешние SMTP."""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = SMTP_USER
    msg['Subject'] = f"🔔 Изменен статус задачи #{task_id}"

    body = (
        f"Привет!\n\n"
        f"В системе произошло событие с задачей:\n"
        f"- ID задачи: {task_id}\n"
        f"- ID Пользователя: {user_id}\n"
        f"- Статус: {status}\n\n"
        f"Удачи в выполнении!"
    )
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.sendmail(SMTP_USER, SMTP_USER, msg.as_string())
        logger.info(f" [✉] Тестовое письмо по задаче #{task_id} успешно отправлено!")
        return True
    except Exception as e:
        logger.error(f" [!] Ошибка отправки Email: {e}")
        return False

def process_task(ch, method, properties, body):
    """Обработчик сообщений из RabbitMQ. Синхронизирован с форматом rabbitmq.py."""
    try:
        data = json.loads(body.decode('utf-8'))
        logger.info(f" [x] Получено событие из RabbitMQ: {data}")
        
        # Извлекаем ключи, которые отправляет rabbitmq.py
        task_id = data.get("task_id", "N/A")
        user_id = data.get("user_id", "N/A")
        status = data.get("status", "unknown")
        
        logger.info(f" [... ] Начинаем обработку уведомления для задачи #{task_id}...")
        send_email_notification(task_id, user_id, status)
        
        # Подтверждаем успешную обработку сообщения брокеру
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f" [✓] Событие по задаче #{task_id} успешно обработано и подтверждено!")
        
    except Exception as e:
        logger.error(f" [!] Ошибка при обработке сообщения в воркере: {e}")
        # Возвращаем сообщение в очередь, если произошел системный сбой
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    # 1. Сначала проверяем переменную через Pydantic-конфиг, если нет — берем напрямую из os.getenv
    RABBITMQ_URL = settings.RABBITMQ_URL if settings else os.getenv("RABBITMQ_URL")
    
    if RABBITMQ_URL:
        # Настройка для Render (CloudAMQP)
        logger.info(" [*] Воркер: Инициализация подключения через RABBITMQ_URL...")
        parameters = pika.URLParameters(RABBITMQ_URL)
    else:
        # Резервный вариант для локального Docker-окружения
        logger.info(f" [*] Воркер: Локальный запуск. Подключение к хосту {RABBITMQ_HOST}...")
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=5672, credentials=credentials)
    
    while True:
        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Создаем отказоустойчивую очередь в CloudAMQP
            channel.queue_declare(queue='task_created_queue', durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='task_created_queue', on_message_callback=process_task)
            
            logger.info(' [*] Фоновый воркер успешно запущен в потоке и ожидает сообщений...')
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f" [!] Ошибка подключения воркера к RabbitMQ ({e}). Повтор через 5 секунд...")
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info(' [*] Воркер принудительно остановлен.')
            break

if __name__ == '__main__':
    main()
