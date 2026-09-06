"""
Lincoln's net - Admin Routes
Complete API endpoints for the entire admin panel
All sections: Auth, Dashboard, Users, Hotspot, Plans, Packages, Settings, Payments, TV Devices
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
# PYDANTIC MODELS
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


class SaveAllSettingsRequest(BaseModel):
    settings: Dict[str, str] = Field(..., description="Dictionary of setting_key: setting_value")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


# ============================================================================
# SECTION 1: AUTHENTICATION
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
# SECTION 2: DASHBOARD API
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
        
        total_transactions = await db.scalar(select(func.count()).select_from(BillingTransaction)) or 0
        total_packages = await db.scalar(select(func.count()).select_from(InternetPackage)) or 0
        total_tv_devices = await db.scalar(select(func.count()).select_from(TVDevice)) or 0
        
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
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/manual-radius-sync")
async def manual_radius_sync_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Manually sync a transaction to RADIUS."""
    try:
        data = await request.json()
        transaction_id = data.get("transaction_id", "")
        
        if not transaction_id:
            return JSONResponse(status_code=400, content={"success": False, "error": "Transaction ID required"})
        
        result = await db.execute(select(BillingTransaction).where(BillingTransaction.transaction_id == transaction_id))
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return JSONResponse(status_code=404, content={"success": False, "error": "Transaction not found"})
        
        if transaction.status != 'SUCCESS':
            return JSONResponse(status_code=400, content={"success": False, "error": "Transaction is not successful"})
        
        result = await db.execute(select(InternetPackage).where(InternetPackage.id == transaction.package_id))
        package = result.scalar_one_or_none()
        
        if not package:
            return JSONResponse(status_code=404, content={"success": False, "error": "Package not found"})
        
        try:
            await sync_to_radius(transaction.mac_address, package.duration_seconds, package.download_rate_limit, package.upload_rate_limit)
            return {"success": True, "message": "RADIUS sync completed", "mac_address": transaction.mac_address, "package": package.name}
        except Exception as sync_error:
            return JSONResponse(status_code=500, content={"success": False, "error": f"RADIUS sync failed: {str(sync_error)}"})
    except Exception as e:
        logger.error(f"Manual sync error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# SECTION 3: USER MANAGEMENT API
# ============================================================================

@router.get("/api/users")
async def get_users_api(
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get all users with statistics."""
    try:
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
        
        if search:
            query = query.where(BillingTransaction.phone_number.contains(search))
        
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await db.scalar(count_query) or 0
        
        query = query.order_by(desc('last_seen')).limit(limit).offset(offset)
        result = await db.execute(query)
        users_data = result.all()
        
        users = []
        for row in users_data:
            active_session = await db.scalar(
                select(func.count()).select_from(BillingTransaction)
                .where(and_(
                    BillingTransaction.phone_number == row.phone_number,
                    BillingTransaction.status == 'SUCCESS',
                    BillingTransaction.expires_at > datetime.utcnow()
                ))
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
        
        if status:
            users = [u for u in users if u['status'] == status]
        
        return {"success": True, "users": users, "total": total_count, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Get users error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/users-stats")
async def get_users_stats_api(db: AsyncSession = Depends(get_db)):
    """Get user statistics for cards."""
    try:
        total_users = await db.scalar(select(func.count(func.distinct(BillingTransaction.phone_number))).select_from(BillingTransaction)) or 0
        active_users = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.phone_number)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
        ) or 0
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.phone_number)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.created_at >= today_start)
        ) or 0
        total_revenue = await db.scalar(
            select(func.coalesce(func.sum(BillingTransaction.amount), 0))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
        ) or 0
        
        return {"success": True, "total_users": total_users, "active_users": active_users, "new_today": new_today, "total_revenue": float(total_revenue)}
    except Exception as e:
        logger.error(f"User stats error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/users/{phone_number}")
async def get_user_details_api(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Get user details with transaction history."""
    try:
        result = await db.execute(select(BillingTransaction).where(BillingTransaction.phone_number == phone_number).order_by(desc(BillingTransaction.created_at)))
        transactions = result.scalars().all()
        
        if not transactions:
            return JSONResponse(status_code=404, content={"success": False, "error": "User not found"})
        
        total_spent = sum(float(tx.amount) for tx in transactions if tx.status == 'SUCCESS')
        transaction_count = len(transactions)
        
        active_session = None
        for tx in transactions:
            if tx.status == 'SUCCESS' and tx.expires_at and tx.expires_at > datetime.utcnow():
                active_session = tx
                break
        
        package_ids = [tx.package_id for tx in transactions if tx.package_id]
        packages_result = await db.execute(select(InternetPackage).where(InternetPackage.id.in_(package_ids)))
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
        result = await db.execute(
            select(BillingTransaction).where(and_(
                BillingTransaction.phone_number == phone_number,
                BillingTransaction.status == 'SUCCESS',
                BillingTransaction.expires_at > datetime.utcnow()
            ))
        )
        transactions = result.scalars().all()
        
        for tx in transactions:
            tx.status = 'EXPIRED'
            tx.is_blocked = True
        
        await db.commit()
        return {"success": True, "message": f"User {phone_number} blocked"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/users/{phone_number}/unblock")
async def unblock_user_api(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Unblock a user."""
    try:
        result = await db.execute(select(BillingTransaction).where(BillingTransaction.phone_number == phone_number))
        transactions = result.scalars().all()
        
        for tx in transactions:
            tx.is_blocked = False
        
        await db.commit()
        return {"success": True, "message": f"User {phone_number} unblocked"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# SECTION 4: HOTSPOT USERS API
# ============================================================================

@router.get("/api/hotspot-users")
async def get_hotspot_users_api(
    search: Optional[str] = None,
    plan_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get active hotspot users."""
    try:
        query = (
            select(BillingTransaction, InternetPackage.name, InternetPackage.download_rate_limit, InternetPackage.upload_rate_limit)
            .join(InternetPackage, BillingTransaction.package_id == InternetPackage.id)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
            .where(BillingTransaction.is_blocked == False)
        )
        
        if search:
            query = query.where(or_(BillingTransaction.phone_number.contains(search), BillingTransaction.mac_address.contains(search)))
        if plan_filter:
            query = query.where(InternetPackage.name == plan_filter)
        
        query = query.order_by(BillingTransaction.expires_at.asc())
        result = await db.execute(query)
        active_connections = result.all()
        
        users = []
        for tx, package_name, download_rate, upload_rate in active_connections:
            time_left = tx.expires_at - datetime.utcnow()
            hours_left = time_left.total_seconds() / 3600
            status = 'active' if hours_left > 1 else ('expiring' if hours_left > 0.25 else 'critical')
            
            users.append({
                "transaction_id": tx.transaction_id,
                "phone_number": tx.phone_number,
                "mac_address": tx.mac_address,
                "device_type": tx.device_type,
                "package_name": package_name,
                "download_rate": download_rate,
                "upload_rate": upload_rate,
                "amount": float(tx.amount),
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
                "expires_at": tx.expires_at.isoformat() if tx.expires_at else None,
                "time_left_seconds": int(time_left.total_seconds()),
                "status": status,
            })
        
        return {"success": True, "users": users, "total": len(users)}
    except Exception as e:
        logger.error(f"Hotspot users error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/hotspot-stats")
async def get_hotspot_stats_api(db: AsyncSession = Depends(get_db)):
    """Get hotspot statistics."""
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        active_connections = await db.scalar(select(func.count()).select_from(BillingTransaction).where(BillingTransaction.status == 'SUCCESS').where(BillingTransaction.expires_at > now)) or 0
        today_connections = await db.scalar(select(func.count()).select_from(BillingTransaction).where(BillingTransaction.created_at >= today_start)) or 0
        expiring_soon = await db.scalar(select(func.count()).select_from(BillingTransaction).where(BillingTransaction.status == 'SUCCESS').where(BillingTransaction.expires_at > now).where(BillingTransaction.expires_at < now + timedelta(hours=1))) or 0
        today_revenue = await db.scalar(select(func.coalesce(func.sum(BillingTransaction.amount), 0)).select_from(BillingTransaction).where(BillingTransaction.status == 'SUCCESS').where(BillingTransaction.created_at >= today_start)) or 0
        
        return {"success": True, "active_connections": active_connections, "today_connections": today_connections, "expiring_soon": expiring_soon, "today_revenue": float(today_revenue)}
    except Exception as e:
        logger.error(f"Hotspot stats error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/hotspot-users/{mac_address}")
async def get_hotspot_user_details_api(mac_address: str, db: AsyncSession = Depends(get_db)):
    """Get single hotspot user details."""
    try:
        result = await db.execute(
            select(BillingTransaction, InternetPackage.name)
            .join(InternetPackage, BillingTransaction.package_id == InternetPackage.id)
            .where(BillingTransaction.mac_address == mac_address)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
            .limit(1)
        )
        connection = result.first()
        
        if not connection:
            return JSONResponse(status_code=404, content={"success": False, "error": "Connection not found"})
        
        tx, package_name = connection
        time_left = tx.expires_at - datetime.utcnow()
        
        return {
            "success": True,
            "connection": {
                "transaction_id": tx.transaction_id,
                "phone_number": tx.phone_number,
                "mac_address": tx.mac_address,
                "package_name": package_name,
                "amount": float(tx.amount),
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
                "expires_at": tx.expires_at.isoformat() if tx.expires_at else None,
                "time_left_seconds": int(time_left.total_seconds()),
            },
        }
    except Exception as e:
        logger.error(f"Hotspot user details error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/hotspot-users/{mac_address}/disconnect")
async def disconnect_hotspot_user_api(mac_address: str, db: AsyncSession = Depends(get_db)):
    """Disconnect hotspot user."""
    try:
        result = await db.execute(select(BillingTransaction).where(and_(
            BillingTransaction.mac_address == mac_address,
            BillingTransaction.status == 'SUCCESS',
            BillingTransaction.expires_at > datetime.utcnow()
        )))
        transactions = result.scalars().all()
        
        for tx in transactions:
            tx.status = 'EXPIRED'
        
        await db.commit()
        return {"success": True, "message": f"User {mac_address} disconnected"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/hotspot-users/{mac_address}/extend")
async def extend_hotspot_user_api(request: Request, mac_address: str, db: AsyncSession = Depends(get_db)):
    """Extend hotspot user session."""
    try:
        data = await request.json()
        extend_seconds = data.get("extend_seconds", 3600)
        
        result = await db.execute(select(BillingTransaction).where(and_(
            BillingTransaction.mac_address == mac_address,
            BillingTransaction.status == 'SUCCESS',
            BillingTransaction.expires_at > datetime.utcnow()
        )))
        transactions = result.scalars().all()
        
        for tx in transactions:
            tx.expires_at = tx.expires_at + timedelta(seconds=extend_seconds)
        
        await db.commit()
        return {"success": True, "message": f"Session extended by {extend_seconds // 60} minutes"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# SECTION 5: PLANS API
# ============================================================================

@router.get("/api/plans-stats")
async def get_plans_stats_api(db: AsyncSession = Depends(get_db)):
    """Get plans statistics."""
    try:
        total_plans = await db.scalar(select(func.count()).select_from(InternetPackage)) or 0
        active_plans = await db.scalar(select(func.count()).select_from(InternetPackage).where(InternetPackage.is_active == True)) or 0
        tv_plans = await db.scalar(select(func.count()).select_from(InternetPackage).where(InternetPackage.supports_tv == True)) or 0
        avg_price = await db.scalar(select(func.coalesce(func.avg(InternetPackage.price), 0)).select_from(InternetPackage)) or 0
        
        popular_result = await db.execute(
            select(InternetPackage.name, func.count(BillingTransaction.id).label('usage_count'))
            .join(BillingTransaction, BillingTransaction.package_id == InternetPackage.id)
            .where(BillingTransaction.status == 'SUCCESS')
            .group_by(InternetPackage.name)
            .order_by(desc('usage_count'))
            .limit(1)
        )
        popular = popular_result.first()
        
        return {
            "success": True,
            "total_plans": total_plans,
            "active_plans": active_plans,
            "tv_plans": tv_plans,
            "avg_price": float(avg_price),
            "most_popular": popular[0] if popular else None,
            "most_popular_count": popular[1] if popular else 0,
        }
    except Exception as e:
        logger.error(f"Plans stats error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/packages/{package_id}/duplicate")
async def duplicate_package_api(package_id: int, db: AsyncSession = Depends(get_db)):
    """Duplicate a package."""
    try:
        result = await db.execute(select(InternetPackage).where(InternetPackage.id == package_id))
        package = result.scalar_one_or_none()
        
        if not package:
            return JSONResponse(status_code=404, content={"success": False, "error": "Package not found"})
        
        duplicate = InternetPackage(
            name=f"{package.name} (Copy)",
            description=package.description,
            price=package.price,
            duration_seconds=package.duration_seconds,
            download_rate_limit=package.download_rate_limit,
            upload_rate_limit=package.upload_rate_limit,
            max_users=package.max_users,
            supports_tv=package.supports_tv,
            is_active=True,
        )
        
        db.add(duplicate)
        await db.commit()
        await db.refresh(duplicate)
        
        return {"success": True, "package": duplicate.to_dict(), "message": "Package duplicated"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/packages/{package_id}/toggle")
async def toggle_package_api(package_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle package active status."""
    try:
        result = await db.execute(select(InternetPackage).where(InternetPackage.id == package_id))
        package = result.scalar_one_or_none()
        
        if not package:
            return JSONResponse(status_code=404, content={"success": False, "error": "Package not found"})
        
        package.is_active = not package.is_active
        await db.commit()
        await db.refresh(package)
        
        status = "activated" if package.is_active else "deactivated"
        return {"success": True, "package": package.to_dict(), "message": f"Package {status}"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/packages/{package_id}/subscribers")
async def get_package_subscribers_api(package_id: int, db: AsyncSession = Depends(get_db)):
    """Get package subscribers."""
    try:
        active = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.phone_number)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.package_id == package_id)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
        ) or 0
        
        total = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.phone_number)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.package_id == package_id)
        ) or 0
        
        revenue = await db.scalar(
            select(func.coalesce(func.sum(BillingTransaction.amount), 0))
            .select_from(BillingTransaction)
            .where(BillingTransaction.package_id == package_id)
            .where(BillingTransaction.status == 'SUCCESS')
        ) or 0
        
        return {"success": True, "package_id": package_id, "active_subscribers": active, "total_subscribers": total, "total_revenue": float(revenue)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# SECTION 6: PACKAGE CRUD API
# ============================================================================

@router.get("/api/packages")
async def get_packages_api(db: AsyncSession = Depends(get_db)):
    """Get all packages."""
    try:
        result = await db.execute(select(InternetPackage).order_by(InternetPackage.price))
        packages = result.scalars().all()
        return {"success": True, "packages": [p.to_dict() for p in packages], "total": len(packages), "currency": CURRENCY_SYMBOL}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/packages")
async def create_package_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new package."""
    try:
        data = await request.json()
        existing = await db.scalar(select(InternetPackage).where(func.lower(InternetPackage.name) == data.get("name", "").lower()))
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
    """Get specific package."""
    try:
        result = await db.execute(select(InternetPackage).where(InternetPackage.id == package_id))
        package = result.scalar_one_or_none()
        if not package:
            return JSONResponse(status_code=404, content={"success": False, "error": "Package not found"})
        return {"success": True, "package": package.to_dict()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put("/api/packages/{package_id}")
async def update_package_api(package_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Update package."""
    try:
        data = await request.json()
        result = await db.execute(select(InternetPackage).where(InternetPackage.id == package_id))
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
    """Delete (soft delete) package."""
    try:
        result = await db.execute(select(InternetPackage).where(InternetPackage.id == package_id))
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
# SECTION 7: SETTINGS API (ENHANCED WITH NEW ENDPOINTS)
# ============================================================================

@router.get("/api/settings")
async def get_settings_api(db: AsyncSession = Depends(get_db)):
    """Get non-secret system settings."""
    try:
        result = await db.execute(select(SystemSetting))
        settings = result.scalars().all()
        return {"success": True, "settings": [s.to_dict() for s in settings if not s.is_secret]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/settings/all")
async def get_all_settings_api(db: AsyncSession = Depends(get_db)):
    """Get ALL settings grouped by category."""
    try:
        result = await db.execute(select(SystemSetting).order_by(SystemSetting.setting_key))
        settings = result.scalars().all()
        
        categories = {"general": [], "payment": [], "network": [], "features": [], "security": []}
        
        for s in settings:
            key = s.setting_key.lower()
            setting_dict = s.to_dict(include_secret=True)
            
            if 'payment' in key or 'payhero' in key or 'mpesa' in key or 'paybill' in key or 'shortcode' in key or 'passkey' in key or 'webhook' in key:
                categories['payment'].append(setting_dict)
            elif 'mikrotik' in key or 'radius' in key or 'timeout' in key or 'network' in key:
                categories['network'].append(setting_dict)
            elif 'enable' in key or 'support' in key and 'phone' not in key:
                categories['features'].append(setting_dict)
            elif 'admin' in key or 'password' in key or 'secret' in key:
                categories['security'].append(setting_dict)
            else:
                categories['general'].append(setting_dict)
        
        return {"success": True, "categories": categories}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.put("/api/settings")
async def update_setting_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Update single setting."""
    try:
        data = await request.json()
        setting_key = data.get("setting_key")
        setting_value = data.get("setting_value")
        
        result = await db.execute(select(SystemSetting).where(SystemSetting.setting_key == setting_key))
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


@router.post("/api/settings/save-all")
async def save_all_settings_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Save all settings at once."""
    try:
        data = await request.json()
        settings_dict = data.get("settings", {})
        updated = 0
        
        for key, value in settings_dict.items():
            result = await db.execute(select(SystemSetting).where(SystemSetting.setting_key == key))
            setting = result.scalar_one_or_none()
            if setting:
                setting.setting_value = str(value)
                setting.updated_at = datetime.utcnow()
                updated += 1
        
        await db.commit()
        return {"success": True, "message": f"Updated {updated} settings"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/settings/reset")
async def reset_settings_api(db: AsyncSession = Depends(get_db)):
    """Reset settings to defaults."""
    try:
        defaults = {
            'gateway_name': "Lincoln's net",
            'currency': 'KES',
            'timezone': 'Africa/Nairobi',
            'admin_email': 'admin@lincolnsnet.com',
            'support_phone': '+254700000000',
            'tv_support_enabled': 'true',
            'payment_gateway_url': 'https://api.payhero.co.ke',
        }
        
        for key, value in defaults.items():
            result = await db.execute(select(SystemSetting).where(SystemSetting.setting_key == key))
            setting = result.scalar_one_or_none()
            if setting:
                setting.setting_value = value
                setting.updated_at = datetime.utcnow()
        
        await db.commit()
        return {"success": True, "message": "Settings reset to defaults"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/settings/change-password")
async def change_password_api(request: Request, db: AsyncSession = Depends(get_db)):
    """Change admin password."""
    try:
        data = await request.json()
        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")
        
        from config.settings import settings
        if current_password != settings.ADMIN_PASSWORD:
            return JSONResponse(status_code=400, content={"success": False, "error": "Current password is incorrect"})
        
        if len(new_password) < 6:
            return JSONResponse(status_code=400, content={"success": False, "error": "Password must be at least 6 characters"})
        
        result = await db.execute(select(SystemSetting).where(SystemSetting.setting_key == 'admin_password'))
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.setting_value = new_password
            setting.updated_at = datetime.utcnow()
            await db.commit()
            return {"success": True, "message": "Password changed successfully"}
        
        # If setting doesn't exist, create it
        new_setting = SystemSetting(setting_key='admin_password', setting_value=new_password, description='Admin Password', is_secret=True)
        db.add(new_setting)
        await db.commit()
        return {"success": True, "message": "Password set successfully"}
    except Exception as e:
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/settings/test-payment")
async def test_payment_api(db: AsyncSession = Depends(get_db)):
    """Test payment gateway connection."""
    try:
        result = await db.execute(select(SystemSetting).where(SystemSetting.setting_key.in_(['payment_gateway_url', 'payment_webhook_secret'])))
        settings = {s.setting_key: s.setting_value for s in result.scalars().all()}
        
        payment_url = settings.get('payment_gateway_url', 'https://api.payhero.co.ke')
        
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(payment_url)
            
        if response.status_code < 500:
            return {"success": True, "message": "Payment gateway is reachable", "status_code": response.status_code}
        else:
            return {"success": False, "message": f"Payment gateway returned status {response.status_code}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": f"Connection failed: {str(e)}"})


# ============================================================================
# SECTION 8: TRANSACTIONS API
# ============================================================================

@router.get("/api/transactions")
async def get_transactions_api(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get transactions."""
    try:
        result = await db.execute(select(BillingTransaction).order_by(desc(BillingTransaction.created_at)).limit(limit))
        transactions = result.scalars().all()
        return {"success": True, "transactions": [t.to_dict() for t in transactions], "currency": CURRENCY_SYMBOL}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# SECTION 9: TV DEVICES API
# ============================================================================

@router.get("/api/tv-devices")
async def get_tv_devices_api(db: AsyncSession = Depends(get_db)):
    """Get all TV devices."""
    try:
        result = await db.execute(select(TVDevice).order_by(desc(TVDevice.created_at)))
        devices = result.scalars().all()
        return {"success": True, "devices": [d.to_dict() for d in devices]}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
