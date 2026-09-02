"""
Lincoln's net - Main Application
FastAPI application initialization and middleware setup
Optimized for Render deployment with Supabase
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any
import os
import sys

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from config.database import init_db, check_db_connection, engine, AsyncSessionLocal
from src.routes import customer, admin, payment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Templates configuration
templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with graceful startup/shutdown."""
    # Startup
    logger.info("=" * 50)
    logger.info(f"Starting {settings.APP_NAME} WiFi Billing System...")
    logger.info(f"Version: {settings.APP_VERSION}")
    logger.info(f"Environment: {'Production' if not settings.DEBUG else 'Development'}")
    logger.info("=" * 50)
    
    # Check database connection with retry
    db_connected = False
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries and not db_connected:
        if retry_count > 0:
            logger.info(f"Retry attempt {retry_count + 1} of {max_retries}...")
            import asyncio
            await asyncio.sleep(5)  # Wait 5 seconds before retry
        
        db_connected = await check_db_connection()
        retry_count += 1
    
    if db_connected:
        logger.info("✅ Database connection successful")
        
        # Try to initialize database tables
        try:
            await init_db()
            logger.info("✅ Database tables initialized/verified")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize tables: {str(e)}")
            logger.info("Tables may already exist - continuing...")
    else:
        logger.warning("⚠️ Database connection failed - starting in degraded mode")
        logger.info("The server will start but database operations will fail")
        logger.info("Please check your DATABASE_URL and Supabase status")
        # Don't raise exception - allow server to start
        # This way health endpoint can report the issue
    
    logger.info("=" * 50)
    logger.info(f"✅ {settings.APP_NAME} startup complete")
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    logger.info("=" * 50)
    logger.info(f"Shutting down {settings.APP_NAME}...")
    
    # Clean up database connections
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.warning(f"⚠️ Error closing database connections: {str(e)}")
    
    logger.info("=" * 50)


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise-grade WiFi Billing and Captive Portal System with M-Pesa Integration",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else "/api/docs",  # Always show docs
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        settings.BACKEND_URL,
        "http://localhost:3000",
        "http://localhost:8000",
        "*",  # Allow all for now - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(f"📥 Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        # Log response
        logger.info(
            f"📤 Response: {response.status_code} "
            f"({processing_time:.2f}ms) {request.method} {request.url.path}"
        )
        
        return response
    except Exception as e:
        logger.error(f"❌ Error processing request: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(e) if settings.DEBUG else "Internal server error"},
        )


# Error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"❌ Global error: {str(exc)}", exc_info=True)
    
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "path": str(request.url.path),
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    """404 error handler."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found", "path": str(request.url.path)},
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    db_status = await check_db_connection()
    
    health_data = {
        "status": "healthy" if db_status else "degraded",
        "database": "connected" if db_status else "disconnected",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "running",
    }
    
    return health_data


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "status": "running",
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/health",
        "endpoints": {
            "customer_portal": "/portal",
            "admin_dashboard": "/admin/dashboard",
            "payment_callback": "/payment/callback",
        }
    }


# Test database endpoint
@app.get("/test-db", tags=["Health"])
async def test_database():
    """Test database connection endpoint."""
    try:
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT NOW()"))
            current_time = result.scalar()
            
            # Test if tables exist
            result = await session.execute(
                text("SELECT COUNT(*) FROM internet_packages")
            )
            package_count = result.scalar()
            
            return {
                "success": True,
                "database_time": current_time.isoformat(),
                "package_count": package_count,
                "message": "Database connection successful"
            }
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Database connection failed"
            }
        )


# Include routers
app.include_router(customer.router, prefix="", tags=["Customer"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(payment.router, prefix="/payment", tags=["Payment"])


# Print all routes on startup (for debugging)
@app.on_event("startup")
async def print_routes():
    """Print all registered routes."""
    logger.info("Registered routes:")
    for route in app.routes:
        if hasattr(route, "methods"):
            methods = ", ".join(route.methods)
            logger.info(f"  {methods:20s} {route.path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info",
        workers=1,  # Use 1 worker for free tier
    )
