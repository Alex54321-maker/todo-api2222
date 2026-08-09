import os
from loguru import logger

# Используем /tmp/logs, так как у Render есть права на запись в папку /tmp
LOG_DIR = "/tmp/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger.add(
    os.path.join(LOG_DIR, "app.log"),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    rotation="10 MB",
    compression="zip"
)
