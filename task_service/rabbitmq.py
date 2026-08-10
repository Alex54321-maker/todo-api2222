import json
import pika
import ssl  # Важно: добавляем модуль SSL
from config import settings
from core.logger import logger

def send_task_created_event(task_id: int, user_id: int):
    """Отправляет событие создания новой задачи в брокер сообщений RabbitMQ с поддержкой SSL."""
    connection = None
    try:
        # Инициализируем параметры подключения через URL
        parameters = pika.URLParameters(settings.RABBITMQ_URL)
        
        # --- ФИКС ДЛЯ ОБЛАЧНОГО SSL (amqps://) ---
        if settings.RABBITMQ_URL.startswith("amqps"):
            logger.info("🔒 [RabbitMQ] Обнаружен защищенный протокол amqps. Настраиваем SSL-контекст...")
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            parameters.ssl_options = pika.SSLOptions(context)
            
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Гарантируем существование очереди
        channel.queue_declare(queue='task_created_queue', durable=True)
        
        # Формируем тело сообщения (payload)
        payload = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "created"
        }
        
        # Публикуем сообщение в дефолтный exchange
        channel.basic_publish(
            exchange='',
            routing_key='task_created_queue',
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Персистентное хранение сообщения
            )
        )
        logger.info(f"🚀 [RabbitMQ] Событие для задачи #{task_id} успешно опубликовано.")
        
    except pika.exceptions.AMQPError as e:
        logger.error(f"❌ [RabbitMQ] Не удалось отправить событие для задачи #{task_id}: {e}")
        raise e
        
    finally:
        # Гарантированно закрываем соединение
        if connection and connection.is_open:
            connection.close()
