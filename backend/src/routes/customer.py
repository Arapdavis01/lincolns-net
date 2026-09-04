"""
Lincoln's net - Customer Routes
Customer-facing API endpoints for portal and payment
Returns JSON only (frontend handles UI)
"""

from src.models.app_models import InternetPackage, BillingTransaction, SystemSetting, TVDevice
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from config.database import get_db
from typing import Optional, Dict, Any
import logging
import uuid
import phonenumbers
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()

CURRENCY_SYMBOL = "KES"


# ============================================================================
# PUBLIC API ENDPOINTS
# ============================================================================

@router.get("/api/packages")
async def get_available_packages(db: AsyncSession = Depends(get_db)):
    """
    Get all active internet packages for customer portal.
    Returns JSON with package details.
    """
    try:
        result = await db.execute(
            select(InternetPackage)
            .where(InternetPackage.is_active == True)
            .order_by(InternetPackage.price)
        )
        packages = result.scalars().all()
        
        return {
            "success": True,
            "packages": [pkg.to_dict() for pkg in packages],
            "currency": CURRENCY_SYMBOL,
        }
    except Exception as e:
        logger.error(f"Error fetching packages: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/settings/public")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    """
    Get public settings for customer portal.
    Returns support phone and TV support status.
    """
    try:
        result = await db.execute(
            select(SystemSetting).where(
                and_(
                    SystemSetting.is_secret == False,
                    SystemSetting.setting_key.in_([
                        'support_phone',
                        'tv_support_enabled',
                        'gateway_name',
                        'currency',
                    ])
                )
            )
        )
        settings = result.scalars().all()
        
        settings_dict = {s.setting_key: s.setting_value for s in settings}
        
        return {
            "success": True,
            "support_phone": settings_dict.get('support_phone', '+254700000000'),
            "tv_support_enabled": settings_dict.get('tv_support_enabled', 'true').lower() == 'true',
            "gateway_name": settings_dict.get('gateway_name', "Lincoln's net"),
            "currency": settings_dict.get('currency', 'KES'),
        }
    except Exception as e:
        logger.error(f"Error fetching settings: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/api/check-active-session")
async def check_active_session(
    mac: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a MAC address has an active session.
    Used for "Already Paid?" feature.
    """
    try:
        if not mac:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "MAC address required"}
            )
        
        # Validate MAC format
        if not validate_mac_address(mac):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Invalid MAC address"}
            )
        
        # Check for active transaction
        result = await db.execute(
            select(BillingTransaction)
            .where(
                and_(
                    BillingTransaction.mac_address == mac,
                    BillingTransaction.status == 'SUCCESS',
                    BillingTransaction.expires_at > datetime.utcnow()
                )
            )
            .order_by(BillingTransaction.expires_at.desc())
            .limit(1)
        )
        transaction = result.scalar_one_or_none()
        
        if transaction:
            return {
                "success": True,
                "has_active_session": True,
                "transaction": transaction.to_dict(include_package=True),
                "message": "Active session found",
            }
        else:
            return {
                "success": True,
                "has_active_session": False,
                "message": "No active session found",
            }
    except Exception as e:
        logger.error(f"Error checking session: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.post("/api/pay")
async def initiate_payment(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate payment for selected package.
    Accepts JSON body.
    """
    try:
        data = await request.json()
        
        package_id = data.get("package_id")
        phone_number = data.get("phone_number")
        mac = data.get("mac", "")
        ip = data.get("ip", "")
        link_login_only = data.get("link_login_only", "")
        device_type = data.get("device_type", "phone")
        
        # Validate inputs
        if not package_id or not phone_number:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Missing package_id or phone_number"}
            )
        
        # Validate phone number
        try:
            parsed_phone = phonenumbers.parse(phone_number, "KE")
            if not phonenumbers.is_valid_number(parsed_phone):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "Invalid phone number format"}
                )
            phone_number = phonenumbers.format_number(
                parsed_phone,
                phonenumbers.PhoneNumberFormat.E164
            )
        except phonenumbers.NumberParseException:
            # Try basic validation if phonenumbers fails
            if not re.match(r'^\+?[0-9]{10,15}$', phone_number):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "Invalid phone number"}
                )
        
        # Fetch package
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == int(package_id))
        )
        package = result.scalar_one_or_none()
        
        if not package or not package.is_active:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Package not found or inactive"}
            )
        
        # Check device limit if max_users > 1
        if package.max_users > 1 and mac:
            active_devices = await db.scalar(
                select(func.count()).select_from(BillingTransaction)
                .where(
                    and_(
                        BillingTransaction.package_id == package.id,
                        BillingTransaction.status == 'SUCCESS',
                        BillingTransaction.expires_at > datetime.utcnow()
                    )
                )
            ) or 0
            
            if active_devices >= package.max_users:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": f"This package allows max {package.max_users} devices"}
                )
        
        # Create billing transaction
        transaction = BillingTransaction(
            transaction_id=str(uuid.uuid4()),
            phone_number=phone_number,
            amount=package.price,
            mac_address=mac,
            package_id=package.id,
            status="PENDING",
            device_type=device_type,
        )
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        
        logger.info(f"Payment initiated: {transaction.transaction_id} - {phone_number} - KES {package.price}")
        
        return {
            "success": True,
            "transaction_id": transaction.transaction_id,
            "amount": float(package.price),
            "currency": CURRENCY_SYMBOL,
            "phone_number": phone_number,
            "message": "Payment initiated. Check your phone for M-Pesa prompt.",
        }
    except Exception as e:
        logger.error(f"Payment initiation error: {str(e)}", exc_info=True)
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# TV CONNECTION ENDPOINT
# ============================================================================

@router.post("/api/connect-tv")
async def connect_tv(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Connect a TV device.
    Accepts TV MAC address and package selection.
    """
    try:
        data = await request.json()
        tv_mac = data.get("tv_mac", "")
        package_id = data.get("package_id")
        phone_number = data.get("phone_number", "")
        
        # Validate MAC address
        if not validate_mac_address(tv_mac):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Invalid TV MAC address"}
            )
        
        # Check if TV already connected
        existing_tv = await db.scalar(
            select(TVDevice).where(TVDevice.mac_address == tv_mac)
        )
        
        if existing_tv and existing_tv.is_active and not existing_tv.is_expired():
            return {
                "success": True,
                "already_connected": True,
                "message": "TV is already connected",
                "device": existing_tv.to_dict(),
            }
        
        # If package provided, create TV device with package
        if package_id:
            result = await db.execute(
                select(InternetPackage).where(InternetPackage.id == int(package_id))
            )
            package = result.scalar_one_or_none()
            
            if not package or not package.supports_tv:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "Package does not support TV connections"}
                )
            
            # Create or update TV device
            if existing_tv:
                existing_tv.package_id = package.id
                existing_tv.is_active = True
                existing_tv.expires_at = datetime.utcnow() + timedelta(seconds=package.duration_seconds)
                await db.commit()
                return {
                    "success": True,
                    "message": "TV connected successfully",
                    "device": existing_tv.to_dict(),
                }
            else:
                tv_device = TVDevice(
                    mac_address=tv_mac,
                    package_id=package.id,
                    is_active=True,
                    expires_at=datetime.utcnow() + timedelta(seconds=package.duration_seconds),
                )
                db.add(tv_device)
                await db.commit()
                await db.refresh(tv_device)
                return {
                    "success": True,
                    "message": "TV connected successfully",
                    "device": tv_device.to_dict(),
                }
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Package ID required for TV connection"}
            )
    except Exception as e:
        logger.error(f"TV connection error: {str(e)}")
        await db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds // 60} minutes"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"
    elif seconds < 2592000:
        weeks = seconds // 604800
        return f"{weeks} week{'s' if weeks != 1 else ''}"
    else:
        months = seconds // 2592000
        return f"{months} month{'s' if months != 1 else ''}"


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format."""
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return bool(mac_pattern.match(mac))


def generate_payment_url(transaction_id: str, phone: str, amount: float, package_name: str) -> str:
    """Generate payment gateway URL."""
    from config.settings import settings
    return f"{settings.PAYMENT_GATEWAY_URL}/pay?txn={transaction_id}&phone={phone}&amount={amount}&desc={package_name}"
