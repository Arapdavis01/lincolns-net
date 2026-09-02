"""
Lincoln's net - Customer Routes
Customer-facing portal and payment initiation
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from config.database import get_db
from typing import Optional
import logging
import uuid
import phonenumbers

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/portal", response_class=HTMLResponse)
async def customer_portal(
    request: Request,
    mac: Optional[str] = None,
    ip: Optional[str] = None,
    link_login_only: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Render the customer captive portal page.
    Displays available internet packages for selection.
    """
    try:
        # Fetch active internet packages
        result = await db.execute(
            select(
                InternetPackage.id,
                InternetPackage.name,
                InternetPackage.description,
                InternetPackage.price,
                InternetPackage.duration_seconds,
                InternetPackage.download_rate_limit,
                InternetPackage.upload_rate_limit
            ).where(InternetPackage.is_active == True)
            .order_by(InternetPackage.price)
        )
        packages = result.all()
        
        # Convert to list of dictionaries
        package_list = [
            {
                "id": pkg[0],
                "name": pkg[1],
                "description": pkg[2],
                "price": f"${pkg[3]:.2f}",
                "duration_seconds": pkg[4],
                "duration_display": format_duration(pkg[4]),
                "download_rate": pkg[5],
                "upload_rate": pkg[6],
            }
            for pkg in packages
        ]
        
        # Validate MAC address format
        if mac and not validate_mac_address(mac):
            logger.warning(f"Invalid MAC address format: {mac}")
            mac = None
        
        return templates.TemplateResponse(
            "portal.html",
            {
                "request": request,
                "packages": package_list,
                "mac_address": mac or "",
                "ip_address": ip or "",
                "link_login_only": link_login_only or "",
                "app_name": "Lincoln's net",
            }
        )
    except Exception as e:
        logger.error(f"Error rendering portal: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/pay", response_class=HTMLResponse)
async def initiate_payment(
    request: Request,
    mac: Optional[str] = None,
    ip: Optional[str] = None,
    link_login_only: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate payment flow for selected package.
    Creates billing transaction and redirects to payment gateway.
    """
    try:
        # Parse form data
        form_data = await request.form()
        package_id = form_data.get("package_id")
        phone_number = form_data.get("phone_number")
        
        # Validate inputs
        if not package_id or not phone_number:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields"}
            )
        
        # Validate phone number
        try:
            parsed_phone = phonenumbers.parse(phone_number, "KE")
            if not phonenumbers.is_valid_number(parsed_phone):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid phone number format"}
                )
            phone_number = phonenumbers.format_number(
                parsed_phone, 
                phonenumbers.PhoneNumberFormat.E164
            )
        except phonenumbers.NumberParseException:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid phone number"}
            )
        
        # Validate MAC address
        if not mac or not validate_mac_address(mac):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid MAC address"}
            )
        
        # Fetch package details
        result = await db.execute(
            select(InternetPackage).where(InternetPackage.id == int(package_id))
        )
        package = result.scalar_one_or_none()
        
        if not package or not package.is_active:
            return JSONResponse(
                status_code=404,
                content={"error": "Package not found or inactive"}
            )
        
        # Create billing transaction
        transaction = BillingTransaction(
            transaction_id=str(uuid.uuid4()),
            phone_number=phone_number,
            amount=package.price,
            mac_address=mac,
            package_id=package.id,
            status="PENDING",
        )
        
        db.add(transaction)
        await db.commit()
        
        # Generate payment gateway URL
        payment_url = generate_payment_url(
            transaction.transaction_id,
            phone_number,
            package.price,
            package.name
        )
        
        # Return payment page or redirect
        return templates.TemplateResponse(
            "payment_redirect.html",
            {
                "request": request,
                "payment_url": payment_url,
                "transaction_id": transaction.transaction_id,
                "amount": package.price,
                "phone_number": phone_number,
                "package_name": package.name,
            }
        )
        
    except Exception as e:
        logger.error(f"Error initiating payment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Payment initiation failed")


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 3600:
        return f"{seconds // 60} minutes"
    elif seconds < 86400:
        return f"{seconds // 3600} hours"
    elif seconds < 604800:
        return f"{seconds // 86400} days"
    elif seconds < 2592000:
        return f"{seconds // 604800} weeks"
    else:
        return f"{seconds // 2592000} months"


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format."""
    import re
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return bool(mac_pattern.match(mac))


def generate_payment_url(transaction_id: str, phone: str, amount: float, package_name: str) -> str:
    """Generate payment gateway URL."""
    from config.settings import settings
    return f"{settings.PAYMENT_GATEWAY_URL}/pay?txn={transaction_id}&phone={phone}&amount={amount}&desc={package_name}"
