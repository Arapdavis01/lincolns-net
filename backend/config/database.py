"""
Lincoln's net - Database Configuration
Optimized for Supabase connection on Render with PgBouncer support
Fixed: Removed incorrect await on fetchone() and scalar()
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
# Database Configuration
# ============================================================================

# Supabase connection details
DB_HOST = os.getenv("DB_HOST", "db.hguhufmlxltksqswwles.supabase.co")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Arapdavis@1954")

# Supabase Pooler (for cloud services like Render)
DB_POOLER_HOST = os.getenv("DB_POOLER_HOST", "aws-1-eu-west-1.pooler.supabase.com")
DB_POOLER_PORT = int(os.getenv("DB_POOLER_PORT", "6543"))
DB_POOLER_USER = os.getenv("DB_POOLER_USER", "postgres.hguhufmlxltksqswwles")

# Supabase project reference
SUPABASE_PROJECT_REF = "hguhufmlxltksqswwles"


def get_database_url() -> str:
    """
    Get database URL with multiple fallback strategies.
    
    Priority:
    1. DATABASE_URL environment variable (if properly set)
    2. Supabase Pooler connection (best for cloud services)
    3. Direct connection (fallback)
    """
    
    # Strategy 1: Use DATABASE_URL if set correctly
    db_url = os.getenv("DATABASE_URL")
    if db_url and not db_url.startswith("DATABASE_URL="):
        # Ensure asyncpg driver
        if "postgresql://" in db_url and "postgresql+asyncpg://" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        logger.info("Using DATABASE_URL from environment")
        return db_url
    
    # Strategy 2: Use Supabase Pooler (recommended for Render)
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    
    pooler_url = (
        f"postgresql+asyncpg://{DB_POOLER_USER}:{encoded_password}"
        f"@{DB_POOLER_HOST}:{DB_POOLER_PORT}/{DB_NAME}"
    )
    
    logger.info(f"Using Supabase Pooler: {DB_POOLER_HOST}:{DB_POOLER_PORT}")
    return pooler_url


DATABASE_URL = get_database_url()

# Log database connection info (without password)
if '@' in DATABASE_URL:
    db_host = DATABASE_URL.split('@')[1].split('/')[0]
    logger.info(f"Database host: {db_host}")
else:
    logger.info("Database URL configured")

# ============================================================================
# Create Async Engine
# ============================================================================

# Create async engine with proper settings for Supabase PgBouncer
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_timeout=30,
    connect_args={
        "ssl": "require",
        "statement_cache_size": 0,  # CRITICAL: Fix for PgBouncer prepared statements
        "command_timeout": 30,
        "timeout": 30,
        "server_settings": {
            "application_name": "lincolns_net",
            "search_path": "public",
        },
    },
)

# ============================================================================
# Session Factory
# ============================================================================

# Create async session factory
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
        async with engine.begin() as conn:
            # Import models to ensure they're registered
            from src.models.app_models import InternetPackage, BillingTransaction, SystemSetting
            from src.models.payment_gateway import PaymentGatewayAccount, PaymentGatewayConfig, PaymentGatewayLog
            
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables initialized/verified")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize tables: {str(e)}")
        logger.info("Tables may already exist - continuing...")


async def check_db_connection() -> bool:
    """
    Check database connectivity with retry logic.
    Returns True if connection successful.
    
    NOTE: fetchone() and scalar() are SYNCHRONOUS methods.
    Do NOT use await on them!
    """
    max_retries = 5
    retry_delay = 3  # seconds
    
    for attempt in range(max_retries):
        try:
            async with engine.connect() as conn:
                # Execute query (this IS async)
                result = await conn.execute(text("SELECT 1"))
                
                # Fetch result (this is NOT async - no await!)
                row = result.fetchone()
                
                # Check if we got a result
                if row is not None:
                    logger.info("✅ Database connection successful")
                    return True
                else:
                    logger.error("Database returned no result")
                    
        except Exception as e:
            logger.error(
                f"Database connection attempt {attempt + 1}/{max_retries} failed: {str(e)}"
            )
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
    
    logger.error("❌ All database connection attempts failed")
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
            # Test basic query - use scalar() WITHOUT await
            result = await session.execute(text("SELECT NOW()"))
            current_time = result.scalar()  # NO await!
            
            # Test if tables exist
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM internet_packages")
                )
                package_count = result.scalar()  # NO await!
            except:
                package_count = 0
            
            # Test if payment gateway tables exist
            try:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM payment_gateway_accounts")
                )
                gateway_count = result.scalar()  # NO await!
            except:
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
    """
    try:
        async with AsyncSessionLocal() as session:
            # Count packages - use scalar() WITHOUT await
            result = await session.execute(
                text("SELECT COUNT(*) FROM internet_packages")
            )
            total_packages = result.scalar()  # NO await!
            
            # Count active packages
            result = await session.execute(
                text("SELECT COUNT(*) FROM internet_packages WHERE is_active = TRUE")
            )
            active_packages = result.scalar()  # NO await!
            
            # Count transactions
            result = await session.execute(
                text("SELECT COUNT(*) FROM billing_transactions")
            )
            total_transactions = result.scalar()  # NO await!
            
            # Count successful transactions
            result = await session.execute(
                text("SELECT COUNT(*) FROM billing_transactions WHERE status = 'SUCCESS'")
            )
            successful_transactions = result.scalar()  # NO await!
            
            return {
                "total_packages": total_packages or 0,
                "active_packages": active_packages or 0,
                "total_transactions": total_transactions or 0,
                "successful_transactions": successful_transactions or 0,
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
