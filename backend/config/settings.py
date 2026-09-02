"""
Lincoln's net - Configuration Settings
Enterprise-grade WiFi Billing System
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://lincolnsnet:password@localhost:5432/lincolnsnet"
    )
    
    # Application Settings
    APP_NAME: str = "Lincoln's net"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Security Settings
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "lincolnsnet2024")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Payment Gateway Settings
    PAYMENT_GATEWAY_URL: str = os.getenv("PAYMENT_GATEWAY_URL", "https://payment-gateway.example.com")
    PAYMENT_WEBHOOK_SECRET: str = os.getenv("PAYMENT_WEBHOOK_SECRET", "webhook-secret-key")
    
    # MikroTik/RADIUS Settings
    RADIUS_SECRET: str = os.getenv("RADIUS_SECRET", "radius-secret-key")
    MIKROTIK_IP: str = os.getenv("MIKROTIK_IP", "192.168.88.1")
    MIKROTIK_LOGIN_URL: str = os.getenv("MIKROTIK_LOGIN_URL", "http://192.168.88.1/login")
    
    # CORS Settings
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://lincolns-net.vercel.app")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "https://lincolns-net.onrender.com")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
