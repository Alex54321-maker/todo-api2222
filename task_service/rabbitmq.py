import json
import pika
from config import settings
from core.logger import logger

def send_task_created_event(task_id: int, user_id: int):
    """Отправляет событие создания новой задачи в брокер сообщений RabbitMQ."""
    connection = None
    try:
        # Инициализируем параметры подключения через URL из Pydantic-настроек
        parameters = pika.URLParameters(settings.RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Гарантируем существование очереди (durable=True для сохранности при перезапуске брокера)
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
                delivery_mode=2,  # Персистентное хранение сообщения на диске брокера
            )
        )
        logger.info(f"🚀 [RabbitMQ] Событие для задачи #{task_id} успешно опубликовано.")
        
    except pika.exceptions.AMQPError as e:
        logger.error(f"❌ [RabbitMQ] Не удалось отправить событие для задачи #{task_id}: {e}")
        raise e
        
    finally:
        # Гарантированно закрываем соединение, если оно было успешно открыто
        if connection and connection.is_open:
            connection.close()
