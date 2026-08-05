import os
import time
import json
import pika

def process_task(ch, method, properties, body):
    """Функция обратного вызова для обработки сообщений из очереди."""
    try:
        # Десериализация JSON
        data = json.loads(body.decode('utf-8'))
        print(f" [x] Получено событие создания задачи: {data}", flush=True)
        
        # Имитация тяжелой работы
        print(" [... ] Начинаем обработку (отправка email / расчет)...", flush=True)
        time.sleep(3)  # имитируем долгую операцию
        
        print(f" [✓] Задача успешно обработана!", flush=True)
        
        # Подтверждаем успешное получение и обработку сообщения
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f" [!] Ошибка при обработке сообщения: {e}", flush=True)
        # В случае ошибки возвращаем сообщение в очередь
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    # Читаем URL из переменной окружения Docker, либо берем localhost для локальных тестов
    rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
    
    print(f" [*] Подключение к RabbitMQ по адресу: {rabbitmq_url}", flush=True)
    
    # Подключаемся через URLParameters (точно так же, как в вашем rabbitmq.py)
    parameters = pika.URLParameters(rabbitmq_url)
    
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    # Объявляем ту же очередь, в которую main.py отправляет сообщения
    channel.queue_declare(queue='task_created_queue', durable=True)
    
    # Распределяем нагрузку: воркер берет только 1 задачу за раз
    channel.basic_qos(prefetch_count=1)
    
    # Регистрируем функцию-обработчик
    channel.basic_consume(queue='task_created_queue', on_message_callback=process_task)
    
    print(' [*] Воркер успешно запущен и ожидает сообщений. Для выхода нажмите CTRL+C', flush=True)
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(' [*] Воркер остановлен.', flush=True)
