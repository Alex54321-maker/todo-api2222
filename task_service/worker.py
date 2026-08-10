import time
import json
import pika
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Ультра-надежный импорт настроек конфигурации
try:
    from task_service.config import settings
    print("✅ [WORKER-DEBUG] Настройки settings успешно импортированы из task_service.config")
except ImportError:
    try:
        from config import settings
        print("✅ [WORKER-DEBUG] Настройки settings успешно импортированы из config")
    except ImportError as e:
        settings = None
        print(f"⚠️ [WORKER-DEBUG] Не удалось импортировать settings: {e}")

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
        print(f" [✉] Тестовое письмо по задаче #{task_id} успешно отправлено!")
        return True
    except Exception as e:
        print(f" [!] Ошибка отправки Email: {e}")
        return False

def process_task(ch, method, properties, body):
    """Обработчик сообщений из RabbitMQ. Синхронизирован с форматом rabbitmq.py."""
    try:
        data = json.loads(body.decode('utf-8'))
        print(f" [x] Получено событие из RabbitMQ: {data}")
        
        # Извлекаем ключи, которые отправляет rabbitmq.py
        task_id = data.get("task_id", "N/A")
        user_id = data.get("user_id", "N/A")
        status = data.get("status", "unknown")
        
        print(f" [... ] Начинаем обработку уведомления для задачи #{task_id}...")
        send_email_notification(task_id, user_id, status)
        
        # Подтверждаем успешную обработку сообщения брокеру
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f" [✓] Событие по задаче #{task_id} успешно обработано и подтверждено!")
        
    except Exception as e:
        print(f" [!] Ошибка при обработке сообщения в воркере: {e}")
        # Возвращаем сообщение в очередь, если произошел системный сбой
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    print("🚀 [WORKER-DEBUG] Функция main() воркера успешно вызвана в потоке!")
    
    # Пытаемся получить URL из всех возможных источников
    RABBITMQ_URL = None
    if settings and hasattr(settings, "RABBITMQ_URL"):
        RABBITMQ_URL = settings.RABBITMQ_URL
    
    if not RABBITMQ_URL:
        RABBITMQ_URL = os.getenv("RABBITMQ_URL")
        
    print(f"🔍 [WORKER-DEBUG] Итоговый RABBITMQ_URL для подключения: {RABBITMQ_URL}")
    
    if RABBITMQ_URL:
        print(" [*] Воркер: Инициализация подключения через URL...")
        parameters = pika.URLParameters(RABBITMQ_URL)
    else:
        print(f" [*] Воркер: Локальный запуск. Подключение к хосту {RABBITMQ_HOST}...")
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=5672, credentials=credentials)
    
    while True:
        try:
            print("⏳ [WORKER-DEBUG] Пробуем открыть BlockingConnection...")
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            print("⏳ [WORKER-DEBUG] Соединение установлено. Создаем очередь task_created_queue...")
            channel.queue_declare(queue='task_created_queue', durable=True)
            
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='task_created_queue', on_message_callback=process_task)
            
            print('🎯 [WORKER-DEBUG] ОЧЕРЕДЬ СОЗДАНА! Воркер успешно ожидает сообщений...')
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ [WORKER-DEBUG] КРИТИЧЕСКАЯ ОШИБКА ПОДКЛЮЧЕНИЯ: {e}")
            print(" Повторная попытка через 5 секунд...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ [WORKER-DEBUG] Непредвиденная ошибка в цикле воркера: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
