from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.routers import cv_processing
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import RequestLoggingMiddleware

def create_application() -> FastAPI:
    settings = get_settings()
    
    app = FastAPI(
        title="CV Processing API",
        description="Production-ready API for CV parsing and ranking",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    #app.add_middleware(RequestLoggingMiddleware)
    #app.add_middleware(RateLimitMiddleware)
    
    # Include routers
    app.include_router(
        cv_processing.router,
        tags=["CV Processing"]
    )
    
    return app

app = create_application() 