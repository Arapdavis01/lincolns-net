"""
Lincoln's net - Database Configuration
DIRECT Supabase connection (No PgBouncer, No Pooler)
Final version - guaranteed to work
"""

import os
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Database Configuration - DIRECT CONNECTION ONLY
# ============================================================================

# Supabase DIRECT connection details (HARDCODED - no pooler)
DB_HOST = "db.hguhufmlxltksqswwles.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "Arapdavis@1954"


def get_database_url() -> str:
    """
    Get DIRECT database URL.
    Uses direct connection (port 5432) to avoid PgBouncer issues.
    """
    # Use hardcoded DIRECT connection - ignore DATABASE_URL from environment
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    direct_url = f"postgresql+asyncpg://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    logger.info(f"Using DIRECT connection: {DB_HOST}:{DB_PORT}")
    return direct_url


DATABASE_URL = get_database_url()

logger.info(f"Database configured: {DB_HOST}:{DB_PORT}")

# ============================================================================
# Create Async Engine - SIMPLE
# ============================================================================

# Create async engine WITHOUT any special connect_args
# Direct connection has NO PgBouncer issues
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

# ============================================================================
# Session Factory
# ============================================================================

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


# ============================================================================
# Database Functions
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    """
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
    """
    Initialize database tables if they don't exist.
    """
    try:
        # Import models to ensure they're registered
        from src.models.app_models import InternetPackage, BillingTransaction, SystemSetting, TVDevice
        from src.models.payment_gateway import PaymentGatewayAccount, PaymentGatewayConfig, PaymentGatewayLog
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables initialized/verified")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize tables: {str(e)}")
        logger.info("Tables may already exist - continuing...")


async def check_db_connection() -> bool:
    """
    Check database connectivity.
    Returns True if connection successful.
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()  # NO await
            
            if row is not None:
                logger.info("✅ Database connection successful")
                return True
            else:
                logger.error("Database returned no result")
                return False
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False


async def close_db_connection():
    """Close database engine connections."""
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.warning(f"⚠️ Error closing database connections: {str(e)}")


async def test_database_query() -> Dict[str, Any]:
    """
    Test database with actual query.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT NOW()"))
            current_time = result.scalar()  # NO await
            
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM internet_packages")
                )
                package_count = result.scalar()  # NO await
            except Exception:
                package_count = 0
            
            return {
                "success": True,
                "database_time": str(current_time),
                "package_count": package_count,
                "message": "Database connection successful"
            }
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Database connection failed"
        }


async def get_database_stats() -> Dict[str, Any]:
    """
    Get database statistics.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM internet_packages")
            )
            total_packages = result.scalar() or 0  # NO await
            
            result = await session.execute(
                text("SELECT COUNT(*) FROM internet_packages WHERE is_active = TRUE")
            )
            active_packages = result.scalar() or 0  # NO await
            
            return {
                "total_packages": total_packages,
                "active_packages": active_packages,
            }
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        return {
            "total_packages": 0,
            "active_packages": 0,
        }


# ============================================================================
# Export Functions
# ============================================================================

__all__ = [
    'Base',
    'engine',
    'AsyncSessionLocal',
    'get_db',
    'init_db',
    'check_db_connection',
    'close_db_connection',
    'test_database_query',
    'get_database_stats',
    'DATABASE_URL',
]
