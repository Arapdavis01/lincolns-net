"""
Lincoln's net - Configuration Settings
Optimized for Render deployment
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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DB_HOST: str = os.getenv("DB_HOST", "db.hguhufmlxltksqswwles.supabase.co")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "Arapdavis@1954")
    
    # Application Settings
    APP_NAME: str = "Lincoln's net"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Security Settings
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "lincolnsnet2024")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Payment Gateway Settings
    PAYMENT_GATEWAY_URL: str = os.getenv("PAYMENT_GATEWAY_URL", "https://api.payhero.co.ke")
    PAYMENT_WEBHOOK_SECRET: str = os.getenv("PAYMENT_WEBHOOK_SECRET", "webhook-secret-key")
    
    # MikroTik/RADIUS Settings
    RADIUS_SECRET: str = os.getenv("RADIUS_SECRET", "radius-secret-key")
    MIKROTIK_IP: str = os.getenv("MIKROTIK_IP", "192.168.88.1")
    MIKROTIK_LOGIN_URL: str = os.getenv("MIKROTIK_LOGIN_URL", "http://192.168.88.1/login")
    
    # CORS Settings
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://lincolns-net.vercel.app")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "https://lincolns-net-backend.onrender.com")
    
    # Database Pool Settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
