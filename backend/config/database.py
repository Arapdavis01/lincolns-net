"""
Lincoln's net - Database Configuration
DIRECT Supabase connection (No PgBouncer, No Pooler)
Simplified for maximum reliability on Render
"""

import os
import urllib.parse
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Database Configuration - DIRECT CONNECTION ONLY
# ============================================================================

# Supabase DIRECT connection details
DB_HOST = os.getenv("DB_HOST", "db.hguhufmlxltksqswwles.supabase.co")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Arapdavis@1954")


def get_database_url() -> str:
    """
    Get DIRECT database URL.
    Uses direct connection (port 5432) to avoid PgBouncer issues.
    """
    # Strategy 1: Use DATABASE_URL from environment if set
    db_url = os.getenv("DATABASE_URL")
    if db_url and not db_url.startswith("DATABASE_URL="):
        # Ensure asyncpg driver
        if "postgresql://" in db_url and "postgresql+asyncpg://" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        logger.info("Using DATABASE_URL from environment")
        return db_url
    
    # Strategy 2: Build DIRECT connection URL
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    direct_url = (
        f"postgresql+asyncpg://{DB_USER}:{encoded_password}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    
    logger.info(f"Using DIRECT connection: {DB_HOST}:{DB_PORT}")
    return direct_url


DATABASE_URL = get_database_url()

# Log database host (without password)
if '@' in DATABASE_URL:
    db_host = DATABASE_URL.split('@')[1].split('/')[0]
    logger.info(f"Database host: {db_host}")

# ============================================================================
# Create Async Engine - SIMPLE (No special connect_args)
# ============================================================================

# Create async engine WITHOUT statement_cache_size
# Direct connection doesn't have PgBouncer prepared statement issues
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_timeout=30,
)

# ============================================================================
# Session Factory
# ============================================================================

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Base class for models
Base = declarative_base()


# ============================================================================
# Database Functions
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.
    Ensures proper session cleanup.
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
        from src.models.app_models import InternetPackage, BillingTransaction, SystemSetting
        from src.models.payment_gateway import PaymentGatewayAccount, PaymentGatewayConfig, PaymentGatewayLog
        
        async with engine.begin() as conn:
            # Create tables if they don't exist
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
            # Execute simple query
            result = await conn.execute(text("SELECT 1"))
            
            # Fetch result (NO await on fetchone)
            row = result.fetchone()
            
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
    Returns result dictionary.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Test basic query
            result = await session.execute(text("SELECT NOW()"))
            current_time = result.scalar()  # NO await
            
            # Test if packages table exists
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM internet_packages")
                )
                package_count = result.scalar()  # NO await
            except Exception:
                package_count = 0
            
            # Test if payment gateway tables exist
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM payment_gateway_accounts")
                )
                gateway_count = result.scalar()  # NO await
            except Exception:
                gateway_count = 0
            
            return {
                "success": True,
                "database_time": str(current_time),
                "package_count": package_count,
                "gateway_account_count": gateway_count,
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
    Returns dictionary with counts.
    """
    try:
        async with AsyncSessionLocal() as session:
            # Count packages
            result = await session.execute(
                text("SELECT COUNT(*) FROM internet_packages")
            )
            total_packages = result.scalar() or 0  # NO await
            
            # Count active packages
            result = await session.execute(
                text("SELECT COUNT(*) FROM internet_packages WHERE is_active = TRUE")
            )
            active_packages = result.scalar() or 0  # NO await
            
            # Count transactions
            result = await session.execute(
                text("SELECT COUNT(*) FROM billing_transactions")
            )
            total_transactions = result.scalar() or 0  # NO await
            
            # Count successful transactions
            result = await session.execute(
                text("SELECT COUNT(*) FROM billing_transactions WHERE status = 'SUCCESS'")
            )
            successful_transactions = result.scalar() or 0  # NO await
            
            return {
                "total_packages": total_packages,
                "active_packages": active_packages,
                "total_transactions": total_transactions,
                "successful_transactions": successful_transactions,
            }
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        return {
            "total_packages": 0,
            "active_packages": 0,
            "total_transactions": 0,
            "successful_transactions": 0,
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
