"""
Lincoln's net - Main Application
FastAPI application initialization and middleware setup
Optimized for Render deployment with Supabase
Includes custom admin login and KES currency support
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional
import os
import sys
import asyncio

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from config.database import init_db, check_db_connection, engine, AsyncSessionLocal
from src.routes import customer, admin, payment
from src.auth.admin_auth import get_admin_from_request

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

# Currency symbol
CURRENCY_SYMBOL = "KES"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with graceful startup/shutdown."""
    # Startup
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} WiFi Billing System...")
    logger.info(f"📌 Version: {settings.APP_VERSION}")
    logger.info(f"🌍 Environment: {'Production' if not settings.DEBUG else 'Development'}")
    logger.info(f"💱 Currency: {CURRENCY_SYMBOL}")
    logger.info("=" * 60)
    
    # Check database connection with retry
    db_connected = False
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries and not db_connected:
        if retry_count > 0:
            logger.info(f"🔄 Retry attempt {retry_count + 1} of {max_retries}...")
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
    
    logger.info("=" * 60)
    logger.info(f"✅ {settings.APP_NAME} startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info(f"🛑 Shutting down {settings.APP_NAME}...")
    
    # Clean up database connections
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.warning(f"⚠️ Error closing database connections: {str(e)}")
    
    logger.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise-grade WiFi Billing and Captive Portal System with M-Pesa Integration",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
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
        "https://lincolns-net-frontend.onrender.com",
        "https://lincolns-net-backend.onrender.com",
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
    # Return JSON for API requests
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Resource not found", "path": str(request.url.path)},
        )
    # Return HTML for page requests
    return JSONResponse(
        status_code=404,
        content={"detail": "Page not found", "path": str(request.url.path)},
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
        "currency": CURRENCY_SYMBOL,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "running",
    }
    
    return health_data


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "status": "running",
        "version": settings.APP_VERSION,
        "currency": CURRENCY_SYMBOL,
        "docs": "/api/docs",
        "health": "/health",
        "endpoints": {
            "customer_portal": "/portal",
            "admin_login": "/admin/login",
            "admin_dashboard": "/admin/dashboard",
            "payment_callback": "/payment/callback",
            "test_database": "/test-db",
        }
    }


# Customer portal redirect
@app.get("/portal", response_class=HTMLResponse)
async def customer_portal_redirect():
    """Redirect to customer portal."""
    return RedirectResponse(url=settings.FRONTEND_URL, status_code=302)


# Test database endpoint
@app.get("/test-db", tags=["Health"])
async def test_database():
    """Test database connection endpoint."""
    try:
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            # Test database connection
            result = await session.execute(text("SELECT NOW()"))
            current_time = result.scalar()
            
            # Test if tables exist
            result = await session.execute(
                text("SELECT COUNT(*) FROM internet_packages")
            )
            package_count = result.scalar()
            
            # Test if payment gateway tables exist
            result = await session.execute(
                text("SELECT COUNT(*) FROM payment_gateway_accounts")
            )
            gateway_account_count = result.scalar()
            
            return {
                "success": True,
                "database_time": current_time.isoformat(),
                "package_count": package_count,
                "gateway_account_count": gateway_account_count,
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


# System info endpoint
@app.get("/api/system-info", tags=["System"])
async def system_info():
    """Get system information."""
    db_status = await check_db_connection()
    
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected" if db_status else "disconnected",
        "currency": CURRENCY_SYMBOL,
        "environment": "production" if not settings.DEBUG else "development",
        "server_time": datetime.utcnow().isoformat(),
        "frontend_url": settings.FRONTEND_URL,
        "backend_url": settings.BACKEND_URL,
    }


# Include routers
app.include_router(customer.router, prefix="", tags=["Customer"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(payment.router, prefix="/payment", tags=["Payment"])


# Print all routes on startup (for debugging)
@app.on_event("startup")
async def print_routes():
    """Print all registered routes."""
    logger.info("=" * 60)
    logger.info("📋 Registered routes:")
    for route in app.routes:
        if hasattr(route, "methods"):
            methods = ", ".join(route.methods)
            logger.info(f"  {methods:20s} {route.path}")
    logger.info("=" * 60)


# Root redirect based on user agent
@app.middleware("http")
async def redirect_root(request: Request, call_next):
    """Redirect root to portal for non-API requests."""
    if request.url.path == "/" and not request.headers.get("user-agent", "").startswith("curl"):
        # Let the root endpoint handle it
        pass
    
    response = await call_next(request)
    return response


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))
    
    # Get host from environment or use default
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=settings.DEBUG,
        log_level="info",
        workers=1,  # Use 1 worker for free tier
    )
