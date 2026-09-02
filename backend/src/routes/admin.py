"""
Lincoln's net - Admin Routes
Admin dashboard and management endpoints
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from config.database import get_db
from src.auth.admin_auth import get_admin_session
from typing import Optional, List
from pydantic import BaseModel, Field
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Pydantic models for request validation
class PackageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    duration_seconds: int = Field(..., gt=0)
    download_rate_limit: str = Field(..., pattern=r'^\d+[KMG]$')
    upload_rate_limit: str = Field(..., pattern=r'^\d+[KMG]$')


class PackageUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    duration_seconds: Optional[int] = Field(None, gt=0)
    download_rate_limit: Optional[str] = None
    upload_rate_limit: Optional[str] = None
    is_active: Optional[bool] = None


class SettingUpdate(BaseModel):
    setting_key: str
    setting_value: str


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(get_admin_session)
):
    """
    Admin dashboard with CRUD operations.
    Protected by HTTP Basic Authentication.
    """
    try:
        # Fetch statistics
        total_packages = await db.scalar(select(func.count()).select_from(InternetPackage))
        active_transactions = await db.scalar(
            select(func.count()).select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
        )
        total_revenue = await db.scalar(
            select(func.sum(BillingTransaction.amount)).select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
        )
        
        # Fetch all packages
        packages_result = await db.execute(
            select(InternetPackage).order_by(InternetPackage.price)
        )
        packages = packages_result.scalars().all()
        
        # Fetch recent transactions
        transactions_result = await db.execute(
            select(BillingTransaction)
            .order_by(desc(BillingTransaction.created_at))
            .limit(20)
        )
        transactions = transactions_result.scalars().all()
        
        # Fetch system settings
        settings_result = await db.execute(select(SystemSetting))
        settings = settings_result.scalars().all()
        
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "app_name": "Lincoln's net Administration Console",
                "stats": {
                    "total_packages": total_packages or 0,
                    "active_transactions": active_transactions or 0,
                    "total_revenue": f"${total_revenue or 0:.2f}",
                },
                "packages": packages,
                "transactions": transactions,
                "settings": settings,
            }
        )
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/packages", response_class=JSONResponse)
async def create_package(
    package_data: PackageCreate,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(get_admin_session)
):
    """Create a new internet package."""
    try:
        package = InternetPackage(
            name=package_data.name,
            description=package_data.description,
            price=package_data.price,
            duration_seconds=package_data.duration_seconds,
            download_rate_limit=package_data.download_rate_limit,
            upload_rate_limit=package_data.upload_rate_limit,
        )
        
        db.add(package)
        await db.commit()
        await db.refresh(package)
        
        logger.info(f"Package created: {package.name} (ID: {package.id})")
        return {"success": True, "package": package.to_dict()}
        
    except Exception as e:
        logger.error(f"Error creating package: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create package")


@router.put("/api/packages/{package_id}", response_class=JSONResponse)
async def update_package(
    package_id: int,
    package_data: PackageUpdate,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(get_admin_session)
):
    """Update an existing internet package."""
    try:
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Update fields
        for field, value in package_data.dict(exclude_unset=True).items():
            setattr(package, field, value)
        
        package.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Package updated: {package.name} (ID: {package.id})")
        return {"success": True, "package": package.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating package: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update package")


@router.delete("/api/packages/{package_id}", response_class=JSONResponse)
async def delete_package(
    package_id: int,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(get_admin_session)
):
    """Delete an internet package."""
    try:
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Soft delete
        package.is_active = False
        await db.commit()
        
        logger.info(f"Package deactivated: {package.name} (ID: {package.id})")
        return {"success": True, "message": "Package deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting package: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete package")


@router.get("/api/transactions", response_class=JSONResponse)
async def get_transactions(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(get_admin_session)
):
    """Get billing transactions with optional status filter."""
    try:
        query = select(BillingTransaction).order_by(desc(BillingTransaction.created_at))
        
        if status:
            query = query.where(BillingTransaction.status == status)
        
        query = query.limit(limit)
        result = await db.execute(query)
        transactions = result.scalars().all()
        
        return {
            "success": True,
            "transactions": [t.to_dict() for t in transactions]
        }
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch transactions")


@router.get("/api/settings", response_class=JSONResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(get_admin_session)
):
    """Get system settings."""
    try:
        result = await db.execute(select(SystemSetting))
        settings = result.scalars().all()
        
        return {
            "success": True,
            "settings": [s.to_dict() for s in settings if not s.is_secret]
        }
        
    except Exception as e:
        logger.error(f"Error fetching settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch settings")


@router.put("/api/settings", response_class=JSONResponse)
async def update_setting(
    setting_data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    authenticated: bool = Depends(get_admin_session)
):
    """Update system setting."""
    try:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.setting_key == setting_data.setting_key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        setting.setting_value = setting_data.setting_value
        setting.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Setting updated: {setting.setting_key}")
        return {"success": True, "setting": setting.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating setting: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update setting")
