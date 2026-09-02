"""
Lincoln's net - Database Configuration
Fixed for Supabase connection on Render
"""

import os
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# Get database configuration from environment
DB_HOST = os.getenv("DB_HOST", "db.hguhufmlxltksqswwles.supabase.co")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Arapdavis@1954")

# Try multiple connection options
def get_database_url():
    """Get database URL with fallbacks."""
    
    # Option 1: Direct DATABASE_URL from environment
    db_url = os.getenv("DATABASE_URL")
    if db_url and not db_url.startswith("DATABASE_URL="):
        # Ensure asyncpg driver
        if "postgresql://" in db_url and "postgresql+asyncpg://" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        return db_url
    
    # Option 2: Construct from individual components
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    
    # Direct connection
    direct_url = f"postgresql+asyncpg://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Connection pooler (if available)
    pooler_host = os.getenv("DB_POOLER_HOST", "")
    if pooler_host:
        pooler_url = f"postgresql+asyncpg://{DB_USER}.{DB_HOST.split('.')[0]}:{encoded_password}@{pooler_host}:6543/{DB_NAME}"
        return pooler_url
    
    return direct_url


DATABASE_URL = get_database_url()
print(f"Using database host: {DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'unknown'}")

# Create async engine with SSL
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "ssl": "require",  # Supabase requires SSL
        "timeout": 30,
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Check database connectivity with retries."""
    import asyncio
    
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
    
    return False
