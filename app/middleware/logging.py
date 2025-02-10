import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
import json

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host,
                "headers": dict(request.headers)
            }
        )
        
        # Get request body for logging
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                await self._set_body(request, body)
            except Exception as e:
                logger.warning(f"Could not read request body: {str(e)}")
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "processing_time": process_time,
                "client_ip": request.client.host
            }
        )
        
        return response
    
    async def _set_body(self, request: Request, body: bytes):
        async def receive() -> Message:
            return {"type": "http.request", "body": body}
        
        request._receive = receive 