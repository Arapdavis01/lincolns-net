"""
Lincoln's net - Admin Routes
Admin dashboard with REAL data API endpoints
Includes: 24hr connections, users by plan, active sessions, recent transactions
NEW: Manual RADIUS sync + User Management APIs
"""

from src.models.app_models import InternetPackage, BillingTransaction, SystemSetting, TVDevice
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_, extract, distinct
from config.database import get_db
from src.models.payment_gateway import (
    PaymentGatewayAccount, 
    PaymentGatewayConfig, 
    PaymentGatewayLog
)
from src.services.payhero_service import PayHeroService
from src.services.radius_sync import sync_to_radius
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import logging
from datetime import datetime, timedelta
import json
import re

logger = logging.getLogger(__name__)

router = APIRouter()

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
# AUTHENTICATION
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
            return {"success": True, "message": "Login successful"}
        else:
            return JSONResponse(status_code=401, content={"success": False, "message": "Invalid username or password"})
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})


# ============================================================================
# USER MANAGEMENT API (NEW)
# ============================================================================

@router.get("/api/users")
async def get_users_api(
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users with statistics.
    Groups by phone number with aggregate data.
    """
    try:
        # Base query - group by phone number
        query = (
            select(
                BillingTransaction.phone_number,
                func.count(BillingTransaction.id).label('transaction_count'),
                func.coalesce(func.sum(BillingTransaction.amount), 0).label('total_spent'),
                func.max(BillingTransaction.created_at).label('last_seen'),
                func.min(BillingTransaction.created_at).label('first_seen'),
                func.max(BillingTransaction.mac_address).label('mac_address'),
                func.max(BillingTransaction.device_type).label('device_type'),
            )
            .select_from(BillingTransaction)
            .group_by(BillingTransaction.phone_number)
        )
        
        # Apply search filter
        if search:
            query = query.where(BillingTransaction.phone_number.contains(search))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await db.scalar(count_query) or 0
        
        # Apply pagination
        query = query.order_by(desc('last_seen')).limit(limit).offset(offset)
        
        result = await db.execute(query)
        users_data = result.all()
        
        # Check active status for each user
        users = []
        for row in users_data:
            # Check if user has active session
            active_session = await db.scalar(
                select(func.count()).select_from(BillingTransaction)
                .where(
                    and_(
                        BillingTransaction.phone_number == row.phone_number,
                        BillingTransaction.status == 'SUCCESS',
                        BillingTransaction.expires_at > datetime.utcnow()
                    )
                )
            ) or 0
            
            users.append({
                "phone_number": row.phone_number,
                "mac_address": row.mac_address,
                "device_type": row.device_type or 'phone',
                "transaction_count": row.transaction_count,
                "total_spent": float(row.total_spent),
                "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                "is_active": active_session > 0,
                "status": 'active' if active_session > 0 else 'inactive',
            })
        
        # Filter by status if provided
        if status:
            users = [u for u in users if u['status'] == status]
        
        return {
            "success": True,
            "users": users,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"Get users error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/users-stats")
async def get_users_stats_api(db: AsyncSession = Depends(get_db)):
    """Get user statistics for cards."""
    try:
        # Total unique users
        total_users = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.phone_number)))
            .select_from(BillingTransaction)
        ) or 0
        
        # Active users (have active session)
        active_users = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.phone_number)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
        ) or 0
        
        # New users today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.phone_number)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.created_at >= today_start)
        ) or 0
        
        # Total revenue from all users
        total_revenue = await db.scalar(
            select(func.coalesce(func.sum(BillingTransaction.amount), 0))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
        ) or 0
        
        return {
            "success": True,
            "total_users": total_users,
            "active_users": active_users,
            "new_today": new_today,
            "total_revenue": float(total_revenue),
        }
    except Exception as e:
        logger.error(f"User stats error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/users/{phone_number}")
async def get_user_details_api(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Get user details with transaction history."""
    try:
        # Get user transactions
        result = await db.execute(
            select(BillingTransaction)
            .where(BillingTransaction.phone_number == phone_number)
            .order_by(desc(BillingTransaction.created_at))
        )
        transactions = result.scalars().all()
        
        if not transactions:
            return JSONResponse(status_code=404, content={"success": False, "error": "User not found"})
        
        # Calculate stats
        total_spent = sum(float(tx.amount) for tx in transactions if tx.status == 'SUCCESS')
        transaction_count = len(transactions)
        
        # Check active session
        active_session = None
        for tx in transactions:
            if tx.status == 'SUCCESS' and tx.expires_at and tx.expires_at > datetime.utcnow():
                active_session = tx
                break
        
        # Get package names
        package_ids = [tx.package_id for tx in transactions if tx.package_id]
        packages_result = await db.execute(
            select(InternetPackage).where(InternetPackage.id.in_(package_ids))
        )
        packages = {p.id: p.name for p in packages_result.scalars().all()}
        
        return {
            "success": True,
            "user": {
                "phone_number": phone_number,
                "mac_address": transactions[0].mac_address if transactions else None,
                "device_type": transactions[0].device_type if transactions else 'phone',
                "total_spent": total_spent,
                "transaction_count": transaction_count,
                "first_seen": transactions[-1].created_at.isoformat() if transactions else None,
                "last_seen": transactions[0].created_at.isoformat() if transactions else None,
                "is_active": active_session is not None,
                "active_session": {
                    "transaction_id": active_session.transaction_id,
                    "package_name": packages.get(active_session.package_id, 'Unknown'),
                    "expires_at": active_session.expires_at.isoformat() if active_session.expires_at else None,
                } if active_session else None,
            },
            "transactions": [
                {
                    "transaction_id": tx.transaction_id,
                    "amount": float(tx.amount),
                    "status": tx.status,
                    "package_name": packages.get(tx.package_id, 'Unknown'),
                    "created_at": tx.created_at.isoformat() if tx.created_at else None,
                }
                for tx in transactions[:10]
            ],
        }
    except Exception as e:
        logger.error(f"Get user details error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/users/{phone_number}/block")
async def block_user_api(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Block a user."""
    try:
        # Expire all active sessions for this user
        result = await db.execute(
            select(BillingTransaction).where(
                and_(
                    BillingTransaction.phone_number == phone_number,
                    BillingTransaction.status == 'SUCCESS',
                    BillingTransaction.expires_at > datetime.utcnow()
                )
            )
        )
        transactions = result.scalars().all()
        
        for tx in transactions:
            tx.status = 'EXPIRED'
        
        await db.commit()
        
        return {"success": True, "message": f"User {phone_number} blocked successfully"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/users/{phone_number}/unblock")
async def unblock_user_api(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Unblock a user."""
    return {"success": True, "message": f"User {phone_number} unblocked"}


# ============================================================================
# DASHBOARD API - MAIN STATS (Unchanged)
# ============================================================================

@router.get("/api/dashboard-stats")
async def get_dashboard_stats_api(db: AsyncSession = Depends(get_db)):
    """Get comprehensive dashboard statistics with REAL data."""
    try:
        total_customers = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.phone_number)))
            .select_from(BillingTransaction)
        ) or 0
        
        active_customers = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.mac_address)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
        ) or 0
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue = await db.scalar(
            select(func.coalesce(func.sum(BillingTransaction.amount), 0))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.created_at >= today_start)
        ) or 0
        
        total_revenue = await db.scalar(
            select(func.coalesce(func.sum(BillingTransaction.amount), 0))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
        ) or 0
        
        total_transactions = await db.scalar(
            select(func.count()).select_from(BillingTransaction)
        ) or 0
        
        total_packages = await db.scalar(
            select(func.count()).select_from(InternetPackage)
        ) or 0
        
        total_tv_devices = await db.scalar(
            select(func.count()).select_from(TVDevice)
        ) or 0
        
        return {
            "success": True,
            "total_customers": total_customers,
            "active_customers": active_customers,
            "today_revenue": float(today_revenue),
            "total_revenue": float(total_revenue),
            "total_transactions": total_transactions,
            "total_packages": total_packages,
            "total_tv_devices": total_tv_devices,
            "currency": CURRENCY_SYMBOL,
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# DASHBOARD API - 24HR CONNECTIONS (Unchanged)
# ============================================================================

@router.get("/api/dashboard/connections-24hr")
async def get_connections_24hr_api(db: AsyncSession = Depends(get_db)):
    """Get hourly connection counts for last 24 hours."""
    try:
        now = datetime.utcnow()
        start_time = now - timedelta(hours=24)
        
        result = await db.execute(
            select(
                extract('hour', BillingTransaction.created_at).label('hour'),
                func.count(BillingTransaction.id).label('count')
            )
            .select_from(BillingTransaction)
            .where(BillingTransaction.created_at >= start_time)
            .group_by('hour')
            .order_by('hour')
        )
        
        hourly_data = result.all()
        
        connections = []
        current_hour = now.hour
        
        for i in range(24):
            hour = (current_hour - 23 + i) % 24
            count = 0
            
            for row in hourly_data:
                if row.hour == hour:
                    count = row.count
                    break
            
            connections.append({"hour": f"{hour:02d}:00", "count": count})
        
        return {"success": True, "connections": connections}
    except Exception as e:
        logger.error(f"24hr connections error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# DASHBOARD API - USERS BY PLAN (Unchanged)
# ============================================================================

@router.get("/api/dashboard/users-by-plan")
async def get_users_by_plan_api(db: AsyncSession = Depends(get_db)):
    """Get user count grouped by package/plan."""
    try:
        result = await db.execute(
            select(
                InternetPackage.name.label('plan_name'),
                InternetPackage.id.label('package_id'),
                func.count(BillingTransaction.id).label('user_count')
            )
            .select_from(BillingTransaction)
            .join(InternetPackage, BillingTransaction.package_id == InternetPackage.id)
            .where(BillingTransaction.status == 'SUCCESS')
            .group_by(InternetPackage.name, InternetPackage.id)
            .order_by(func.count(BillingTransaction.id).desc())
        )
        
        plan_data = result.all()
        
        plans = [
            {"package_id": row.package_id, "plan_name": row.plan_name, "user_count": row.user_count}
            for row in plan_data
        ]
        
        return {"success": True, "plans": plans}
    except Exception as e:
        logger.error(f"Users by plan error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# DASHBOARD API - ACTIVE SESSIONS (Unchanged)
# ============================================================================

@router.get("/api/dashboard/active-sessions")
async def get_active_sessions_api(db: AsyncSession = Depends(get_db)):
    """Get currently active sessions with REAL data."""
    try:
        result = await db.execute(
            select(BillingTransaction, InternetPackage.name)
            .join(InternetPackage, BillingTransaction.package_id == InternetPackage.id)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
            .order_by(BillingTransaction.created_at.desc())
            .limit(20)
        )
        
        active_sessions = result.all()
        
        sessions = [
            {
                "transaction_id": tx.transaction_id,
                "phone_number": tx.phone_number,
                "mac_address": tx.mac_address,
                "package_name": package_name,
                "amount": float(tx.amount),
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
                "expires_at": tx.expires_at.isoformat() if tx.expires_at else None,
                "device_type": tx.device_type,
            }
            for tx, package_name in active_sessions
        ]
        
        return {"success": True, "sessions": sessions, "total": len(sessions)}
    except Exception as e:
        logger.error(f"Active sessions error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# DASHBOARD API - RECENT TRANSACTIONS (Unchanged)
# ============================================================================

@router.get("/api/dashboard/recent-transactions")
async def get_recent_transactions_api(limit: int = 5, db: AsyncSession = Depends(get_db)):
    """Get latest 5 transactions."""
    try:
        result = await db.execute(
            select(BillingTransaction)
            .order_by(desc(BillingTransaction.created_at))
            .limit(limit)
        )
        
        transactions = result.scalars().all()
        
        return {
            "success": True,
            "transactions": [
                {
                    "transaction_id": tx.transaction_id,
                    "phone_number": tx.phone_number,
                    "amount": float(tx.amount),
                    "status": tx.status,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None,
                }
                for tx in transactions
            ],
        }
    except Exception as e:
        logger.error(f"Recent transactions error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# DASHBOARD API - DISCONNECT USER (Unchanged)
# ============================================================================

@router.post("/api/disconnect-user")
async def disconnect_user_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Disconnect a user by MAC address."""
    try:
        data = await request.json()
        mac_address = data.get("mac_address", "")
        
        if not mac_address:
            return JSONResponse(status_code=400, content={"success": False, "error": "MAC address required"})
        
        result = await db.execute(
            select(BillingTransaction).where(
                and_(
                    BillingTransaction.mac_address == mac_address,
                    BillingTransaction.status == 'SUCCESS',
                    BillingTransaction.expires_at > datetime.utcnow()
                )
            )
        )
        transactions = result.scalars().all()
        
        for tx in transactions:
            tx.status = 'EXPIRED'
        
        await db.commit()
        
        return {"success": True, "message": "User disconnected successfully"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Disconnect user error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# MANUAL RADIUS SYNC (Unchanged)
# ============================================================================

@router.post("/api/manual-radius-sync")
async def manual_radius_sync_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Manually sync a transaction to RADIUS."""
    try:
        data = await request.json()
        transaction_id = data.get("transaction_id", "")
        
        if not transaction_id:
            return JSONResponse(status_code=400, content={"success": False, "error": "Transaction ID required"})
        
        result = await db.execute(
            select(BillingTransaction)
            .where(BillingTransaction.transaction_id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return JSONResponse(status_code=404, content={"success": False, "error": "Transaction not found"})
        
        if transaction.status != 'SUCCESS':
            return JSONResponse(status_code=400, content={"success": False, "error": "Transaction is not successful"})
        
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == transaction.package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            return JSONResponse(status_code=404, content={"success": False, "error": "Package not found"})
        
        try:
            await sync_to_radius(
                transaction.mac_address,
                package.duration_seconds,
                package.download_rate_limit,
                package.upload_rate_limit
            )
            
            return {
                "success": True,
                "message": "RADIUS sync completed successfully",
                "mac_address": transaction.mac_address,
                "package": package.name,
            }
        except Exception as sync_error:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"RADIUS sync failed: {str(sync_error)}"}
            )
    except Exception as e:
        logger.error(f"Manual sync error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# PACKAGE MANAGEMENT API (Unchanged)
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
        
        return {"success": True, "package": package.to_dict(), "message": "Package created"}
    except Exception as e:
        await db.rollback()
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
        
        for key, value in data.items():
            if hasattr(package, key) and value is not None:
                setattr(package, key, value)
        
        await db.commit()
        await db.refresh(package)
        
        return {"success": True, "package": package.to_dict(), "message": "Package updated"}
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
# SETTINGS API (Unchanged)
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
# TRANSACTIONS API (Unchanged)
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
# TV DEVICES API (Unchanged)
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
