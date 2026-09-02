"""
Lincoln's net - Database Configuration
Optimized for Supabase connection on Render
"""

import os
import urllib.parse
import asyncio
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


def get_database_url():
    """Get database URL with multiple fallback strategies."""
    
    # Strategy 1: Use DATABASE_URL if set correctly
    db_url = os.getenv("DATABASE_URL")
    if db_url and not db_url.startswith("DATABASE_URL="):
        # Ensure asyncpg driver
        if "postgresql://" in db_url and "postgresql+asyncpg://" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        return db_url
    
    # Strategy 2: Construct from individual components
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    
    # Direct connection
    direct_url = f"postgresql+asyncpg://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Strategy 3: Try connection pooler if direct fails
    pooler_host = os.getenv("DB_POOLER_HOST")
    if pooler_host:
        project_ref = DB_HOST.split('.')[0]
        pooler_url = f"postgresql+asyncpg://{DB_USER}.{project_ref}:{encoded_password}@{pooler_host}:6543/{DB_NAME}"
        return pooler_url
    
    return direct_url


DATABASE_URL = get_database_url()

# Log database connection info (without password)
if '@' in DATABASE_URL:
    db_host = DATABASE_URL.split('@')[1].split('/')[0]
    logger.info(f"Database host: {db_host}")
else:
    logger.info("Database URL configured")

# Create async engine with proper SSL settings
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "ssl": "require",  # Supabase requires SSL
        "server_settings": {
            "application_name": "lincolns_net",
        },
        "timeout": 30,
    },
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for models
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


async def init_db():
    """Initialize database tables if they don't exist."""
    try:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.warning(f"Could not initialize tables: {str(e)}")
        logger.info("Tables may already exist - continuing...")


async def check_db_connection() -> bool:
    """Check database connectivity with retry logic."""
    max_retries = 3
    retry_delay = 3  # seconds
    
    for attempt in range(max_retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                logger.info("✅ Database connection successful")
                return True
        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
    
    logger.error("❌ All database connection attempts failed")
    return False
