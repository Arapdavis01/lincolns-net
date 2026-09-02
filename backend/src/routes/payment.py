"""
Lincoln's net - Payment Routes
Payment webhook callback handling
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends  # ← ADD Depends HERE
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config.database import get_db
from config.settings import settings
from src.services.radius_sync import sync_to_radius
from typing import Optional
import logging
import hashlib
import hmac
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/callback", response_class=JSONResponse)
async def payment_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle payment gateway webhook callback.
    Processes successful payments and triggers RADIUS sync.
    """
    try:
        # Get webhook payload
        payload = await request.json()
        
        # Verify webhook signature (if provided)
        signature = request.headers.get("X-Webhook-Signature")
        if signature and not verify_webhook_signature(payload, signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Extract transaction details
        transaction_id = payload.get("transaction_id")
        status = payload.get("status")
        payment_reference = payload.get("payment_reference")
        
        if not transaction_id or not status:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields"}
            )
        
        # Fetch transaction from database
        result = await db.execute(
            select(BillingTransaction).where(
                BillingTransaction.transaction_id == transaction_id
            )
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            logger.error(f"Transaction not found: {transaction_id}")
            return JSONResponse(
                status_code=404,
                content={"error": "Transaction not found"}
            )
        
        # Update transaction status
        if status == "SUCCESS":
            transaction.status = "SUCCESS"
            transaction.payment_reference = payment_reference
            
            # Calculate expiration time
            package_result = await db.execute(
                select(InternetPackage).where(
                    InternetPackage.id == transaction.package_id
                )
            )
            package = package_result.scalar_one_or_none()
            
            if package:
                transaction.expires_at = datetime.utcnow() + timedelta(
                    seconds=package.duration_seconds
                )
            
            await db.commit()
            
            # Sync to RADIUS in background
            background_tasks.add_task(
                sync_to_radius,
                transaction.mac_address,
                package.duration_seconds if package else 3600,
                package.download_rate_limit if package else "1M",
                package.upload_rate_limit if package else "1M"
            )
            
            logger.info(f"Payment successful for transaction: {transaction_id}")
            
        elif status == "FAILED":
            transaction.status = "FAILED"
            await db.commit()
            logger.info(f"Payment failed for transaction: {transaction_id}")
            
        else:
            logger.warning(f"Unknown payment status: {status}")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid status"}
            )
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "status": transaction.status
        }
        
    except Exception as e:
        logger.error(f"Error processing payment callback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status/{transaction_id}", response_class=JSONResponse)
async def payment_status(
    transaction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check payment status for a transaction.
    Used by frontend to poll for payment completion.
    """
    try:
        result = await db.execute(
            select(BillingTransaction).where(
                BillingTransaction.transaction_id == transaction_id
            )
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return JSONResponse(
                status_code=404,
                content={"error": "Transaction not found"}
            )
        
        return {
            "transaction_id": transaction.transaction_id,
            "status": transaction.status,
            "amount": float(transaction.amount),
            "phone_number": transaction.phone_number,
            "created_at": transaction.created_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error checking payment status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


def verify_webhook_signature(payload: dict, signature: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.
    """
    try:
        # Create expected signature
        secret = settings.PAYMENT_WEBHOOK_SECRET.encode('utf-8')
        message = str(payload).encode('utf-8')
        expected_signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        return False
