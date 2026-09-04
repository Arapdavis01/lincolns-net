"""
Lincoln's net - Admin Routes
Admin dashboard and management endpoints with PayHero/Safaricom configuration
Includes max_users, supports_tv, and support phone settings
"""

from src.models.app_models import InternetPackage, BillingTransaction, SystemSetting, TVDevice
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_
from config.database import get_db
from src.models.payment_gateway import (
    PaymentGatewayAccount, 
    PaymentGatewayConfig, 
    PaymentGatewayLog
)
from src.services.payhero_service import PayHeroService
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import logging
from datetime import datetime, timedelta
import json
import re

logger = logging.getLogger(__name__)

router = APIRouter()

# Currency symbol
CURRENCY_SYMBOL = "KES"


# ============================================================================
# Pydantic Models
# ============================================================================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class PackageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0)
    duration_seconds: int = Field(..., gt=0)
    download_rate_limit: str = Field(..., pattern=r'^\d+[KMG]$')
    upload_rate_limit: str = Field(..., pattern=r'^\d+[KMG]$')
    max_users: int = Field(default=1, ge=1, le=10)
    supports_tv: bool = Field(default=False)
    
    @validator('price')
    def validate_price(cls, v):
        if round(v, 2) != v:
            raise ValueError('Price must have at most 2 decimal places')
        if v < 1:
            raise ValueError('Price must be at least 1 KES')
        return v


class PackageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    duration_seconds: Optional[int] = Field(None, gt=0)
    download_rate_limit: Optional[str] = Field(None, pattern=r'^\d+[KMG]$')
    upload_rate_limit: Optional[str] = Field(None, pattern=r'^\d+[KMG]$')
    max_users: Optional[int] = Field(None, ge=1, le=10)
    supports_tv: Optional[bool] = None
    is_active: Optional[bool] = None


class SettingUpdate(BaseModel):
    setting_key: str = Field(..., min_length=1, max_length=255)
    setting_value: str = Field(..., min_length=1)


# ============================================================================
# AUTHENTICATION (JSON API)
# ============================================================================

@router.post("/api/login")
async def admin_login_api(request: Request):
    """API endpoint for admin login."""
    try:
        data = await request.json()
        username = data.get("username", "")
        password = data.get("password", "")
        
        from config.settings import settings
        
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            logger.info(f"Admin login successful: {username}")
            return {
                "success": True,
                "message": "Login successful",
                "token": "admin_session_token",
            }
        else:
            logger.warning(f"Failed login attempt: {username}")
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid username or password"}
            )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# ============================================================================
# DASHBOARD API
# ============================================================================

@router.get("/api/dashboard-stats")
async def get_dashboard_stats_api(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics as JSON."""
    try:
        total_packages = await db.scalar(select(func.count()).select_from(InternetPackage)) or 0
        active_packages = await db.scalar(
            select(func.count()).select_from(InternetPackage).where(InternetPackage.is_active == True)
        ) or 0
        
        total_transactions = await db.scalar(select(func.count()).select_from(BillingTransaction)) or 0
        
        total_revenue = await db.scalar(
            select(func.coalesce(func.sum(BillingTransaction.amount), 0))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
        ) or 0
        
        active_customers = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.mac_address)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
        ) or 0
        
        total_tv_devices = await db.scalar(select(func.count()).select_from(TVDevice)) or 0
        
        return {
            "success": True,
            "total_packages": total_packages,
            "active_packages": active_packages,
            "total_transactions": total_transactions,
            "total_revenue": float(total_revenue),
            "active_customers": active_customers,
            "total_tv_devices": total_tv_devices,
            "currency": CURRENCY_SYMBOL,
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# PACKAGE MANAGEMENT API
# ============================================================================

@router.get("/api/packages")
async def get_packages_api(db: AsyncSession = Depends(get_db)):
    """Get all packages."""
    try:
        result = await db.execute(
            select(InternetPackage).order_by(InternetPackage.price)
        )
        packages = result.scalars().all()
        
        return {
            "success": True,
            "packages": [pkg.to_dict() for pkg in packages],
            "total": len(packages),
            "currency": CURRENCY_SYMBOL,
        }
    except Exception as e:
        logger.error(f"Get packages error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/packages")
async def create_package_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new package."""
    try:
        data = await request.json()
        
        # Check for duplicate name
        existing = await db.scalar(
            select(InternetPackage).where(
                func.lower(InternetPackage.name) == data.get("name", "").lower()
            )
        )
        if existing:
            return JSONResponse(status_code=400, content={"success": False, "error": "Package name already exists"})
        
        package = InternetPackage(
            name=data.get("name"),
            description=data.get("description"),
            price=data.get("price"),
            duration_seconds=data.get("duration_seconds"),
            download_rate_limit=data.get("download_rate_limit", "5M"),
            upload_rate_limit=data.get("upload_rate_limit", "2M"),
            max_users=data.get("max_users", 1),
            supports_tv=data.get("supports_tv", False),
        )
        
        db.add(package)
        await db.commit()
        await db.refresh(package)
        
        logger.info(f"Package created: {package.name} (ID: {package.id})")
        return {"success": True, "package": package.to_dict(), "message": "Package created successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Create package error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/packages/{package_id}")
async def get_package_api(package_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific package."""
    try:
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            return JSONResponse(status_code=404, content={"success": False, "error": "Package not found"})
        
        return {"success": True, "package": package.to_dict()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put("/api/packages/{package_id}")
async def update_package_api(package_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Update a package."""
    try:
        data = await request.json()
        
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            return JSONResponse(status_code=404, content={"success": False, "error": "Package not found"})
        
        # Update fields
        for key, value in data.items():
            if hasattr(package, key) and value is not None:
                setattr(package, key, value)
        
        await db.commit()
        await db.refresh(package)
        
        logger.info(f"Package updated: {package.name} (ID: {package.id})")
        return {"success": True, "package": package.to_dict(), "message": "Package updated successfully"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.delete("/api/packages/{package_id}")
async def delete_package_api(package_id: int, db: AsyncSession = Depends(get_db)):
    """Delete (soft delete) a package."""
    try:
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            return JSONResponse(status_code=404, content={"success": False, "error": "Package not found"})
        
        package.is_active = False
        await db.commit()
        
        return {"success": True, "message": "Package deactivated"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# SETTINGS API
# ============================================================================

@router.get("/api/settings")
async def get_settings_api(db: AsyncSession = Depends(get_db)):
    """Get system settings."""
    try:
        result = await db.execute(select(SystemSetting))
        settings = result.scalars().all()
        
        return {
            "success": True,
            "settings": [s.to_dict() for s in settings if not s.is_secret],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put("/api/settings")
async def update_setting_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Update system setting."""
    try:
        data = await request.json()
        setting_key = data.get("setting_key")
        setting_value = data.get("setting_value")
        
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.setting_key == setting_key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            return JSONResponse(status_code=404, content={"success": False, "error": "Setting not found"})
        
        setting.setting_value = setting_value
        setting.updated_at = datetime.utcnow()
        await db.commit()
        
        return {"success": True, "setting": setting.to_dict(), "message": "Setting updated"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# TRANSACTIONS API
# ============================================================================

@router.get("/api/transactions")
async def get_transactions_api(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get transactions."""
    try:
        result = await db.execute(
            select(BillingTransaction)
            .order_by(desc(BillingTransaction.created_at))
            .limit(limit)
        )
        transactions = result.scalars().all()
        
        return {
            "success": True,
            "transactions": [t.to_dict() for t in transactions],
            "currency": CURRENCY_SYMBOL,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# TV DEVICES API
# ============================================================================

@router.get("/api/tv-devices")
async def get_tv_devices_api(db: AsyncSession = Depends(get_db)):
    """Get all TV devices."""
    try:
        result = await db.execute(select(TVDevice).order_by(desc(TVDevice.created_at)))
        devices = result.scalars().all()
        
        return {
            "success": True,
            "devices": [d.to_dict() for d in devices],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
