import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("shortlink")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
_handler.setFormatter(_formatter)
logger.addHandler(_handler)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        status_code = response.status_code
        
        logger.info(
            f"{client_ip} - {method} {path} - {status_code} - {process_time:.2f}ms"
        )
        
        response.headers["X-Process-Time"] = f"{process_time:.2f}"
        return response


def setup_logger(app):
    app.add_middleware(RequestLoggerMiddleware)
