import time
import json
import pika
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Настройки SMTP для работы внутри Docker-сети с контейнером test_mail (Mailpit)
SMTP_SERVER = os.getenv("SMTP_SERVER", "test_mail")
SMTP_PORT = int(os.getenv("SMTP_PORT", 1025))
SMTP_USER = os.getenv("SMTP_USER", "wormsbecher.alexander@gmail.com")

# Имя хоста RabbitMQ в вашей Docker-сети (из вывода docker ps)
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "microservices_rabbitmq")

def send_email_notification(task_title, task_id, user_id):
    """Функция для отправки Email через SMTP Mailpit внутри Docker."""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = SMTP_USER
    msg['Subject'] = f"🔔 Создана новая задача #{task_id}"

    body = (
        f"Привет!\n\n"
        f"В системе зарегистрирована новая задача:\n"
        f"- ID задачи: {task_id}\n"
        f"- Название: {task_title}\n"
        f"- ID Пользователя: {user_id}\n\n"
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
    """Обработчик сообщений из RabbitMQ."""
    try:
        data = json.loads(body.decode('utf-8'))
        print(f" [x] Получено событие: {data}")
        
        task_title = data.get("title", "Без названия")
        task_id = data.get("id", "N/A")
        user_id = data.get("user_id", "N/A")
        
        print(" [... ] Начинаем отправку email-уведомления...")
        send_email_notification(task_title, task_id, user_id)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f" [✓] Событие полностью обработано!")
        
    except Exception as e:
        print(f" [!] Ошибка при обработке сообщения в воркере: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, port=5672, credentials=credentials)
    
    # Бесконечный цикл для автоматического переподключения
    while True:
        try:
            print(f" [*] Попытка подключения к RabbitMQ по адресу: {RABBITMQ_HOST}...")
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            channel.queue_declare(queue='task_created_queue', durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='task_created_queue', on_message_callback=process_task)
            
            print(' [*] Воркер успешно запущен и ожидает сообщений. Для выхода нажмите CTRL+C')
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError:
            print(" [!] Ошибка подключения к RabbitMQ. Повторная попытка через 5 секунд...")
            time.sleep(5)
        except KeyboardInterrupt:
            print(' [*] Воркер остановлен.')
            break

if __name__ == '__main__':
    main()
