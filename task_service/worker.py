import os
import time
import json
import pika
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email_notification(task_data: dict):
    """Формирует и отправляет MIME-уведомление через SMTP (Mailpit)."""
    # Читаем настройки SMTP из окружения (для Docker хост 'mailpit', порт 1025)
    smtp_host = os.getenv("SMTP_HOST", "mailpit")
    smtp_port = int(os.getenv("SMTP_PORT", 1025))
    
    # Извлекаем ID задачи и email (если они есть в теле сообщения)
    task_id = task_data.get("task_id", "Неизвестный ID")

    title = task_data.get("title", "Без названия")
    recipient_email = task_data.get("user_email", "test@example.com") # Подставьте ваш ключ email

    # Создаем MIME-сообщение
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Уведомление: Задача #{task_id} запущена в обработку"
    msg["From"] = "no-reply@taskservice.local"
    msg["To"] = recipient_email

    # HTML-шаблон письма
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #4CAF50;">Успешный запуск задачи!</h2>
        <p>Приветствуем,</p>
        <p>Ваша задача <strong>#{task_id} ("{title}")</strong> была успешно добавлена в очередь и сейчас обрабатывается воркером.</p>
        <hr style="border: 0; border-top: 1px solid #eee;" />
        <small style="color: #777;">Это автоматическое уведомление среды разработки. Пожалуйста, не отвечайте на него.</small>
      </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.sendmail(msg["From"], msg["To"], msg.as_string())
        print(f" [✓] MIME-письмо по задаче #{task_id} отправлено на {recipient_email}", flush=True)
    except Exception as e:
        print(f" [!] Ошибка отправки SMTP-письма для задачи #{task_id}: {e}", flush=True)

def process_task(ch, method, properties, body):
    """Функция обратного вызова для обработки сообщений из очереди."""
    try:
        # Десериализация JSON
        data = json.loads(body.decode('utf-8'))
        print(f" [x] Получено событие создания задачи: {data}", flush=True)
        
        # Имитация тяжелой работы
        print(" [... ] Начинаем обработку и отправку email...", flush=True)
        
        # Отправляем реальное MIME-уведомление в Mailpit
        send_email_notification(data)
        
        time.sleep(3)  # имитируем долгую операцию
        
        print(f" [✓] Задача успешно обработана!", flush=True)
        
        # Подтверждаем успешное получение и обработку сообщения
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f" [!] Ошибка при обработке сообщения: {e}", flush=True)
        # В случае ошибки возвращаем сообщение в queue
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
