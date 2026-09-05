"""
Lincoln's net - Database Configuration
Shared Pooler + NullPool + statement_cache_size=0
ABSOLUTE FINAL VERSION - Works on Render with Supabase PgBouncer
"""

import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Database Configuration - SHARED POOLER
# ============================================================================

# Supabase Shared Pooler connection details
DB_HOST = "aws-1-eu-west-1.pooler.supabase.com"
DB_PORT = 6543
DB_NAME = "postgres"
DB_USER = "postgres.hguhufmlxltksqswwles"
DB_PASSWORD = "Arapdavis@1954"


def get_database_url() -> str:
    """
    Get Shared Pooler database URL.
    Uses pooler (port 6543) - Render CAN reach this.
    """
    # Percent-encode password (handles @ in password)
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    
    pooler_url = (
        f"postgresql+asyncpg://{DB_USER}:{encoded_password}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    
    logger.info(f"Using Shared Pooler: {DB_HOST}:{DB_PORT}")
    return pooler_url


DATABASE_URL = get_database_url()

logger.info(f"Database configured: {DB_HOST}:{DB_PORT}")

# ============================================================================
# Create Async Engine - WITH NullPool + statement_cache_size=0
# ============================================================================

# CRITICAL FIXES:
# 1. NullPool - Disables SQLAlchemy's own connection pooling
#    (SQLAlchemy pooling conflicts with PgBouncer)
# 2. statement_cache_size=0 - Disables prepared statements
#    (PgBouncer doesn't support them)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,  # CRITICAL: No SQLAlchemy pooling
    connect_args={
        "statement_cache_size": 0,  # CRITICAL: No prepared statements
        "prepared_statement_cache_size": 0,  # Alternative setting
        "ssl": "require",
    },
)

# ============================================================================
# Session Factory
# ============================================================================

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
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
            # Execute simple query
            result = await conn.execute(text("SELECT 1"))
            
            # Fetch result (NO await on fetchone - it's synchronous)
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
