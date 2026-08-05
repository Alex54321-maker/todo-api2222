import json
import pika
from config import settings

def send_task_created_event(task_id: int, user_id: int):
    # Подключаемся к RabbitMQ по URL из конфигурации
    parameters = pika.URLParameters(settings.RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Гарантируем существование очереди
    channel.queue_declare(queue='task_created_queue', durable=True)
    
    # Собираем данные события
    payload = {
        "task_id": task_id,
        "user_id": user_id,
        "status": "created"
    }
    
    # Отправляем сообщение
    channel.basic_publish(
        exchange='',
        routing_key='task_created_queue',
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Персистентное хранение сообщения
        )
    )
    connection.close()
