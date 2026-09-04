"""
Lincoln's net - Admin Routes
Admin dashboard and management endpoints with PayHero/Safaricom configuration
Includes custom login page and session management
"""

from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_
from config.database import get_db
from src.auth.admin_auth import (
    get_admin_session,
    verify_admin_login,
    create_admin_session_response,
    clear_admin_session_response,
    get_client_ip,
    get_admin_from_request,
    auth_manager,
)
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
templates = Jinja2Templates(directory="templates")

# Currency symbol for display
CURRENCY_SYMBOL = "KES"


# ============================================================================
# Pydantic Models for Request Validation
# ============================================================================

class LoginRequest(BaseModel):
    """Model for admin login."""
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class PackageCreate(BaseModel):
    """Model for creating a new internet package."""
    name: str = Field(..., min_length=1, max_length=255, description="Package name")
    description: Optional[str] = Field(None, max_length=500, description="Package description")
    price: float = Field(..., gt=0, description="Package price in KES")
    duration_seconds: int = Field(..., gt=0, description="Duration in seconds")
    download_rate_limit: str = Field(..., pattern=r'^\d+[KMG]$', description="Download rate (e.g., 5M)")
    upload_rate_limit: str = Field(..., pattern=r'^\d+[KMG]$', description="Upload rate (e.g., 2M)")
    
    @validator('price')
    def validate_price(cls, v):
        """Validate price has max 2 decimal places."""
        if round(v, 2) != v:
            raise ValueError('Price must have at most 2 decimal places')
        if v < 1:
            raise ValueError('Price must be at least 1 KES')
        return v
    
    @validator('duration_seconds')
    def validate_duration(cls, v):
        """Validate duration is reasonable."""
        if v < 60:
            raise ValueError('Duration must be at least 60 seconds')
        if v > 31536000:  # 1 year
            raise ValueError('Duration cannot exceed 1 year')
        return v


class PackageUpdate(BaseModel):
    """Model for updating an existing package."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    duration_seconds: Optional[int] = Field(None, gt=0)
    download_rate_limit: Optional[str] = Field(None, pattern=r'^\d+[KMG]$')
    upload_rate_limit: Optional[str] = Field(None, pattern=r'^\d+[KMG]$')
    is_active: Optional[bool] = None


class SettingUpdate(BaseModel):
    """Model for updating system settings."""
    setting_key: str = Field(..., min_length=1, max_length=255)
    setting_value: str = Field(..., min_length=1)


class PayHeroAccountCreate(BaseModel):
    """Model for creating a PayHero account."""
    account_name: str = Field(..., min_length=1, max_length=255)
    api_key: str = Field(..., min_length=1, max_length=255)
    api_secret: str = Field(..., min_length=1, max_length=255)
    account_number: Optional[str] = Field(None, max_length=100)
    business_number: Optional[str] = Field(None, max_length=100)
    shortcode: Optional[str] = Field(None, max_length=50)
    passkey: Optional[str] = Field(None, max_length=255)
    consumer_key: Optional[str] = Field(None, max_length=255)
    consumer_secret: Optional[str] = Field(None, max_length=255)
    environment: str = Field(default='sandbox', pattern='^(sandbox|production)$')
    is_active: bool = False
    priority: int = Field(default=0, ge=0, le=100)
    
    @validator('account_name')
    def validate_account_name(cls, v):
        """Validate account name format."""
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError('Account name can only contain letters, numbers, spaces, hyphens, and underscores')
        return v.strip()


class PayHeroAccountUpdate(BaseModel):
    """Model for updating a PayHero account."""
    account_name: Optional[str] = Field(None, min_length=1, max_length=255)
    api_key: Optional[str] = Field(None, min_length=1, max_length=255)
    api_secret: Optional[str] = Field(None, min_length=1, max_length=255)
    account_number: Optional[str] = Field(None, max_length=100)
    business_number: Optional[str] = Field(None, max_length=100)
    shortcode: Optional[str] = Field(None, max_length=50)
    passkey: Optional[str] = Field(None, max_length=255)
    consumer_key: Optional[str] = Field(None, max_length=255)
    consumer_secret: Optional[str] = Field(None, max_length=255)
    environment: Optional[str] = Field(None, pattern='^(sandbox|production)$')
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)


class PayHeroConfigUpdate(BaseModel):
    """Model for updating PayHero configuration."""
    config_key: str = Field(..., min_length=1, max_length=255)
    config_value: str = Field(..., min_length=1)
    
    @validator('config_key')
    def validate_config_key(cls, v):
        """Validate config key format."""
        if not re.match(r'^[a-z0-9_]+$', v):
            raise ValueError('Config key can only contain lowercase letters, numbers, and underscores')
        return v


class DashboardStats(BaseModel):
    """Model for dashboard statistics."""
    total_packages: int = 0
    active_packages: int = 0
    total_transactions: int = 0
    active_transactions: int = 0
    total_revenue: float = 0.0
    today_revenue: float = 0.0
    total_customers: int = 0
    active_customers: int = 0


# ============================================================================
# Authentication Routes
# ============================================================================

@router.get("/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """
    Render custom admin login page.
    """
    # Check if already logged in
    if get_admin_from_request(request):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "admin_login.html",
        {
            "request": request,
            "app_name": "Lincoln's net Administration",
        }
    )


@router.post("/api/login", response_class=JSONResponse)
async def admin_login(
    request: Request,
    login_data: LoginRequest,
):
    """
    API endpoint for admin login.
    """
    ip_address = get_client_ip(request)
    
    success, message = verify_admin_login(
        request,
        login_data.username,
        login_data.password,
        ip_address
    )
    
    if success:
        # Create session
        session_token = auth_manager.create_session(login_data.username)
        
        return {
            "success": True,
            "message": message,
            "redirect_url": "/admin/dashboard",
            "session_token": session_token,
        }
    else:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": message,
            }
        )


@router.get("/logout")
async def admin_logout():
    """
    Logout admin user.
    """
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_session")
    return response


# ============================================================================
# Dashboard Routes
# ============================================================================

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Admin dashboard with CRUD operations and payment gateway configuration.
    """
    # Check if admin is authenticated
    if not get_admin_from_request(request):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        # Fetch comprehensive statistics
        stats = await get_dashboard_stats(db)
        
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
        
        # Fetch payment gateway accounts
        gateway_accounts_result = await db.execute(
            select(PaymentGatewayAccount)
            .where(PaymentGatewayAccount.gateway_type == 'payhero')
            .order_by(PaymentGatewayAccount.priority.desc())
        )
        gateway_accounts = gateway_accounts_result.scalars().all()
        
        # Fetch payment gateway configs
        gateway_configs_result = await db.execute(
            select(PaymentGatewayConfig)
            .where(PaymentGatewayConfig.gateway_type == 'payhero')
        )
        gateway_configs = gateway_configs_result.scalars().all()
        
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "app_name": "Lincoln's net Administration Console",
                "currency": CURRENCY_SYMBOL,
                "stats": {
                    "total_packages": stats.total_packages,
                    "active_packages": stats.active_packages,
                    "total_transactions": stats.total_transactions,
                    "active_transactions": stats.active_transactions,
                    "total_revenue": f"{CURRENCY_SYMBOL} {stats.total_revenue:,.2f}",
                    "today_revenue": f"{CURRENCY_SYMBOL} {stats.today_revenue:,.2f}",
                    "total_customers": stats.total_customers,
                    "active_customers": stats.active_customers,
                },
                "packages": packages,
                "transactions": transactions,
                "settings": settings,
                "gateway_accounts": [acc.to_dict() for acc in gateway_accounts],
                "gateway_configs": [cfg.to_dict() for cfg in gateway_configs],
            }
        )
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
    """Get comprehensive dashboard statistics."""
    try:
        # Package statistics
        total_packages = await db.scalar(select(func.count()).select_from(InternetPackage))
        active_packages = await db.scalar(
            select(func.count()).select_from(InternetPackage)
            .where(InternetPackage.is_active == True)
        )
        
        # Transaction statistics
        total_transactions = await db.scalar(select(func.count()).select_from(BillingTransaction))
        active_transactions = await db.scalar(
            select(func.count()).select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
        )
        
        # Revenue statistics
        total_revenue = await db.scalar(
            select(func.coalesce(func.sum(BillingTransaction.amount), 0.0))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
        )
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue = await db.scalar(
            select(func.coalesce(func.sum(BillingTransaction.amount), 0.0))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.created_at >= today_start)
        )
        
        # Customer statistics
        total_customers = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.mac_address)))
            .select_from(BillingTransaction)
        )
        active_customers = await db.scalar(
            select(func.count(func.distinct(BillingTransaction.mac_address)))
            .select_from(BillingTransaction)
            .where(BillingTransaction.status == 'SUCCESS')
            .where(BillingTransaction.expires_at > datetime.utcnow())
        )
        
        return DashboardStats(
            total_packages=total_packages or 0,
            active_packages=active_packages or 0,
            total_transactions=total_transactions or 0,
            active_transactions=active_transactions or 0,
            total_revenue=float(total_revenue or 0),
            today_revenue=float(today_revenue or 0),
            total_customers=total_customers or 0,
            active_customers=active_customers or 0,
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return DashboardStats()


# ============================================================================
# Package Management Routes
# ============================================================================

@router.get("/api/packages", response_class=JSONResponse)
async def get_packages(
    db: AsyncSession = Depends(get_db),
):
    """Get all internet packages."""
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
        logger.error(f"Error fetching packages: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch packages")


@router.post("/api/packages", response_class=JSONResponse)
async def create_package(
    package_data: PackageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new internet package."""
    try:
        # Check for duplicate package name
        existing = await db.scalar(
            select(InternetPackage).where(
                func.lower(InternetPackage.name) == package_data.name.lower()
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="Package with this name already exists")
        
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
        
        logger.info(f"Package created: {package.name} (ID: {package.id}) - {CURRENCY_SYMBOL} {package.price}")
        return {
            "success": True,
            "package": package.to_dict(),
            "message": "Package created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating package: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create package")


@router.get("/api/packages/{package_id}", response_class=JSONResponse)
async def get_package(
    package_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific internet package."""
    try:
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        return {
            "success": True,
            "package": package.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching package: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch package")


@router.put("/api/packages/{package_id}", response_class=JSONResponse)
async def update_package(
    package_id: int,
    package_data: PackageUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing internet package."""
    try:
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Check for duplicate name if name is being updated
        if package_data.name and package_data.name.lower() != package.name.lower():
            existing = await db.scalar(
                select(InternetPackage).where(
                    and_(
                        func.lower(InternetPackage.name) == package_data.name.lower(),
                        InternetPackage.id != package_id
                    )
                )
            )
            if existing:
                raise HTTPException(status_code=400, detail="Package with this name already exists")
        
        # Update fields
        for field, value in package_data.dict(exclude_unset=True).items():
            setattr(package, field, value)
        
        package.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(package)
        
        logger.info(f"Package updated: {package.name} (ID: {package.id})")
        return {
            "success": True,
            "package": package.to_dict(),
            "message": "Package updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating package: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update package")


@router.delete("/api/packages/{package_id}", response_class=JSONResponse)
async def delete_package(
    package_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete (soft delete) an internet package."""
    try:
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        
        # Soft delete
        package.is_active = False
        package.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Package deactivated: {package.name} (ID: {package.id})")
        return {
            "success": True,
            "message": "Package deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting package: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete package")


# ============================================================================
# Transaction Management Routes
# ============================================================================

@router.get("/api/transactions", response_class=JSONResponse)
async def get_transactions(
    status: Optional[str] = None,
    phone_number: Optional[str] = None,
    mac_address: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get billing transactions with filters."""
    try:
        query = select(BillingTransaction).order_by(desc(BillingTransaction.created_at))
        
        # Apply filters
        if status:
            query = query.where(BillingTransaction.status == status.upper())
        
        if phone_number:
            query = query.where(BillingTransaction.phone_number.contains(phone_number))
        
        if mac_address:
            query = query.where(BillingTransaction.mac_address == mac_address)
        
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from)
                query = query.where(BillingTransaction.created_at >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format")
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to)
                query = query.where(BillingTransaction.created_at <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format")
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await db.scalar(count_query)
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        transactions = result.scalars().all()
        
        return {
            "success": True,
            "transactions": [t.to_dict() for t in transactions],
            "total": total_count or 0,
            "limit": limit,
            "offset": offset,
            "currency": CURRENCY_SYMBOL,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transactions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch transactions")


@router.get("/api/transactions/{transaction_id}", response_class=JSONResponse)
async def get_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific transaction."""
    try:
        result = await db.execute(
            select(BillingTransaction).where(BillingTransaction.transaction_id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {
            "success": True,
            "transaction": transaction.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transaction: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch transaction")


# ============================================================================
# System Settings Routes
# ============================================================================

@router.get("/api/settings", response_class=JSONResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
):
    """Get system settings."""
    try:
        result = await db.execute(select(SystemSetting))
        settings = result.scalars().all()
        
        return {
            "success": True,
            "settings": [s.to_dict() for s in settings if not s.is_secret],
            "total": len(settings)
        }
        
    except Exception as e:
        logger.error(f"Error fetching settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch settings")


@router.put("/api/settings", response_class=JSONResponse)
async def update_setting(
    setting_data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
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
        return {
            "success": True,
            "setting": setting.to_dict(),
            "message": "Setting updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating setting: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update setting")


# ============================================================================
# PayHero/Safaricom Payment Gateway Routes
# ============================================================================

@router.get("/payment-gateway/accounts", response_class=JSONResponse)
async def get_payment_gateway_accounts(
    db: AsyncSession = Depends(get_db),
):
    """Get all payment gateway accounts."""
    try:
        result = await db.execute(
            select(PaymentGatewayAccount)
            .where(PaymentGatewayAccount.gateway_type == 'payhero')
            .order_by(PaymentGatewayAccount.priority.desc())
        )
        accounts = result.scalars().all()
        
        return {
            "success": True,
            "accounts": [acc.to_dict() for acc in accounts],
            "total": len(accounts)
        }
        
    except Exception as e:
        logger.error(f"Error fetching payment gateway accounts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch payment gateway accounts")


@router.get("/payment-gateway/accounts/{account_id}", response_class=JSONResponse)
async def get_payment_gateway_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific payment gateway account."""
    try:
        result = await db.execute(
            select(PaymentGatewayAccount).where(PaymentGatewayAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return {
            "success": True,
            "account": account.to_dict(include_secrets=True)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payment gateway account: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch payment gateway account")


@router.post("/payment-gateway/accounts", response_class=JSONResponse)
async def create_payment_gateway_account(
    account_data: PayHeroAccountCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new PayHero payment gateway account."""
    try:
        # Check for duplicate account name
        existing = await db.scalar(
            select(PaymentGatewayAccount).where(
                func.lower(PaymentGatewayAccount.account_name) == account_data.account_name.lower()
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="Account with this name already exists")
        
        payhero_service = PayHeroService(db)
        
        # If this is the first account or marked as active, deactivate others
        account_count = await db.scalar(
            select(func.count()).select_from(PaymentGatewayAccount)
        )
        
        if account_count == 0 or account_data.is_active:
            account_data.is_active = True
        
        result = await payhero_service.create_account(account_data.dict())
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to create account'))
        
        # Optionally test the connection in background
        if account_data.is_active:
            background_tasks.add_task(
                payhero_service.test_connection,
                result['account']['id']
            )
        
        logger.info(f"PayHero account created: {account_data.account_name}")
        return {
            "success": True,
            "account": result['account'],
            "message": "Payment gateway account created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment gateway account: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create payment gateway account")


@router.put("/payment-gateway/accounts/{account_id}", response_class=JSONResponse)
async def update_payment_gateway_account(
    account_id: int,
    account_data: PayHeroAccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a PayHero payment gateway account."""
    try:
        # Check if account exists
        result = await db.execute(
            select(PaymentGatewayAccount).where(PaymentGatewayAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Check for duplicate name if name is being updated
        if account_data.account_name and account_data.account_name.lower() != account.account_name.lower():
            existing = await db.scalar(
                select(PaymentGatewayAccount).where(
                    and_(
                        func.lower(PaymentGatewayAccount.account_name) == account_data.account_name.lower(),
                        PaymentGatewayAccount.id != account_id
                    )
                )
            )
            if existing:
                raise HTTPException(status_code=400, detail="Account with this name already exists")
        
        payhero_service = PayHeroService(db)
        result = await payhero_service.update_account(
            account_id,
            account_data.dict(exclude_unset=True)
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to update account'))
        
        logger.info(f"PayHero account updated: {account_id}")
        return {
            "success": True,
            "account": result['account'],
            "message": "Payment gateway account updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment gateway account: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update payment gateway account")


@router.delete("/payment-gateway/accounts/{account_id}", response_class=JSONResponse)
async def delete_payment_gateway_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a PayHero payment gateway account."""
    try:
        # Check if account exists
        result = await db.execute(
            select(PaymentGatewayAccount).where(PaymentGatewayAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Prevent deletion of the only active account
        if account.is_active:
            active_count = await db.scalar(
                select(func.count()).select_from(PaymentGatewayAccount)
                .where(PaymentGatewayAccount.is_active == True)
            )
            if active_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete the only active account. Please activate another account first."
                )
        
        payhero_service = PayHeroService(db)
        result = await payhero_service.delete_account(account_id)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to delete account'))
        
        logger.info(f"PayHero account deleted: {account_id}")
        return {
            "success": True,
            "message": "Payment gateway account deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payment gateway account: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete payment gateway account")


@router.post("/payment-gateway/accounts/{account_id}/test", response_class=JSONResponse)
async def test_payment_gateway_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Test connection to a PayHero payment gateway account."""
    try:
        payhero_service = PayHeroService(db)
        result = await payhero_service.test_connection(account_id)
        
        if result['success']:
            return {
                "success": True,
                "message": "Connection test successful",
                "details": result.get('response_data', {})
            }
        else:
            return {
                "success": False,
                "message": result.get('error', 'Connection test failed'),
                "details": result.get('response_data', {})
            }
        
    except Exception as e:
        logger.error(f"Error testing payment gateway account: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to test payment gateway account")


@router.post("/payment-gateway/accounts/{account_id}/activate", response_class=JSONResponse)
async def activate_payment_gateway_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Activate a PayHero payment gateway account (deactivates others)."""
    try:
        # Check if account exists
        result = await db.execute(
            select(PaymentGatewayAccount).where(PaymentGatewayAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        payhero_service = PayHeroService(db)
        
        # Activate this account and deactivate others
        result = await payhero_service.update_account(
            account_id,
            {'is_active': True}
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to activate account'))
        
        logger.info(f"PayHero account activated: {account.account_name} (ID: {account_id})")
        return {
            "success": True,
            "message": "Payment gateway account activated successfully",
            "account": result['account']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating payment gateway account: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to activate payment gateway account")


@router.post("/payment-gateway/accounts/{account_id}/deactivate", response_class=JSONResponse)
async def deactivate_payment_gateway_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a PayHero payment gateway account."""
    try:
        # Check if account exists
        result = await db.execute(
            select(PaymentGatewayAccount).where(PaymentGatewayAccount.id == account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Check if this is the only active account
        if account.is_active:
            active_count = await db.scalar(
                select(func.count()).select_from(PaymentGatewayAccount)
                .where(PaymentGatewayAccount.is_active == True)
            )
            if active_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot deactivate the only active account. Please activate another account first."
                )
        
        payhero_service = PayHeroService(db)
        result = await payhero_service.update_account(
            account_id,
            {'is_active': False}
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to deactivate account'))
        
        logger.info(f"PayHero account deactivated: {account.account_name} (ID: {account_id})")
        return {
            "success": True,
            "message": "Payment gateway account deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating payment gateway account: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to deactivate payment gateway account")


@router.get("/payment-gateway/configs", response_class=JSONResponse)
async def get_payment_gateway_configs(
    db: AsyncSession = Depends(get_db),
):
    """Get PayHero payment gateway configurations."""
    try:
        result = await db.execute(
            select(PaymentGatewayConfig)
            .where(PaymentGatewayConfig.gateway_type == 'payhero')
            .order_by(PaymentGatewayConfig.config_key)
        )
        configs = result.scalars().all()
        
        return {
            "success": True,
            "configs": [config.to_dict() for config in configs],
            "total": len(configs)
        }
        
    except Exception as e:
        logger.error(f"Error fetching payment gateway configs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch payment gateway configurations")


@router.put("/payment-gateway/configs", response_class=JSONResponse)
async def update_payment_gateway_config(
    config_data: PayHeroConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update PayHero payment gateway configuration."""
    try:
        result = await db.execute(
            select(PaymentGatewayConfig).where(
                and_(
                    PaymentGatewayConfig.config_key == config_data.config_key,
                    PaymentGatewayConfig.gateway_type == 'payhero'
                )
            )
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        config.config_value = config_data.config_value
        config.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"Payment gateway config updated: {config.config_key}")
        return {
            "success": True,
            "config": config.to_dict(),
            "message": "Configuration updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment gateway config: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.post("/payment-gateway/configs/batch", response_class=JSONResponse)
async def update_payment_gateway_configs_batch(
    configs: List[PayHeroConfigUpdate],
    db: AsyncSession = Depends(get_db),
):
    """Update multiple PayHero payment gateway configurations in batch."""
    try:
        updated_configs = []
        
        for config_data in configs:
            result = await db.execute(
                select(PaymentGatewayConfig).where(
                    and_(
                        PaymentGatewayConfig.config_key == config_data.config_key,
                        PaymentGatewayConfig.gateway_type == 'payhero'
                    )
                )
            )
            config = result.scalar_one_or_none()
            
            if config:
                config.config_value = config_data.config_value
                config.updated_at = datetime.utcnow()
                updated_configs.append(config)
        
        await db.commit()
        
        logger.info(f"Updated {len(updated_configs)} payment gateway configs")
        return {
            "success": True,
            "message": f"Updated {len(updated_configs)} configurations",
            "updated_count": len(updated_configs)
        }
        
    except Exception as e:
        logger.error(f"Error updating payment gateway configs batch: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update configurations")


@router.get("/payment-gateway/logs", response_class=JSONResponse)
async def get_payment_gateway_logs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    transaction_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get PayHero payment gateway transaction logs."""
    try:
        query = select(PaymentGatewayLog).order_by(desc(PaymentGatewayLog.created_at))
        
        if status:
            query = query.where(PaymentGatewayLog.status == status.upper())
        
        if transaction_id:
            query = query.where(PaymentGatewayLog.transaction_id == transaction_id)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await db.scalar(count_query)
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return {
            "success": True,
            "logs": [log.to_dict() for log in logs],
            "total": total_count or 0,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error fetching payment gateway logs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch payment gateway logs")


@router.get("/payment-gateway/summary", response_class=JSONResponse)
async def get_payment_gateway_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get payment gateway summary statistics."""
    try:
        # Get active account
        active_account = await db.execute(
            select(PaymentGatewayAccount)
            .where(
                and_(
                    PaymentGatewayAccount.gateway_type == 'payhero',
                    PaymentGatewayAccount.is_active == True
                )
            )
            .limit(1)
        )
        active_account_data = active_account.scalar_one_or_none()
        
        # Get transaction counts
        total_transactions = await db.scalar(
            select(func.count()).select_from(PaymentGatewayLog)
        )
        
        successful_transactions = await db.scalar(
            select(func.count()).select_from(PaymentGatewayLog)
            .where(PaymentGatewayLog.status == 'SUCCESS')
        )
        
        failed_transactions = await db.scalar(
            select(func.count()).select_from(PaymentGatewayLog)
            .where(PaymentGatewayLog.status == 'FAILED')
        )
        
        return {
            "success": True,
            "summary": {
                "active_account": active_account_data.to_dict() if active_account_data else None,
                "total_transactions": total_transactions or 0,
                "successful_transactions": successful_transactions or 0,
                "failed_transactions": failed_transactions or 0,
                "success_rate": round((successful_transactions / total_transactions * 100) if total_transactions else 0, 2),
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching payment gateway summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch payment gateway summary")
