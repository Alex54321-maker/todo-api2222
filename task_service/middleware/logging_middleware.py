import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.logger import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        method = request.method
        url = request.url.path
        client_host = request.client.host if request.client else "unknown"
        
        logger.info(f"Запрос: {method} {url} | IP: {client_host}")
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            status_code = response.status_code
            log_msg = f"Ответ: {method} {url} | Статус: {status_code} | Время: {process_time:.2f}ms"
            
            if status_code >= 400:
                logger.warning(log_msg)
            else:
                logger.success(log_msg)
                
            return response
            
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.exception(
                f"Ошибка: {method} {url} | Сбой: {str(e)} | Время: {process_time:.2f}ms"
            )
            raise e
