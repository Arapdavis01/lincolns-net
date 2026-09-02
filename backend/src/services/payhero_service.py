"""
Lincoln's net - PayHero Payment Service
Integration with PayHero/Safaricom M-Pesa API
"""

import httpx
import logging
import hashlib
import hmac
import base64
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from config.settings import settings
from src.models.payment_gateway import PaymentGatewayAccount, PaymentGatewayConfig, PaymentGatewayLog

logger = logging.getLogger(__name__)


class PayHeroService:
    """Service for handling PayHero/Safaricom M-Pesa payments."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.base_url = "https://api.payhero.co.ke"
        self.timeout = 30
        self.retry_attempts = 3
    
    async def get_active_account(self) -> Optional[PaymentGatewayAccount]:
        """Get the active PayHero account."""
        try:
            result = await self.db.execute(
                select(PaymentGatewayAccount)
                .where(
                    and_(
                        PaymentGatewayAccount.gateway_type == 'payhero',
                        PaymentGatewayAccount.is_active == True
                    )
                )
                .order_by(PaymentGatewayAccount.priority.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting active PayHero account: {str(e)}")
            return None
    
    async def initialize_payment(
        self,
        phone_number: str,
        amount: float,
        transaction_id: str,
        description: str = None
    ) -> Dict[str, Any]:
        """
        Initialize a PayHero payment.
        
        Args:
            phone_number: Customer phone number
            amount: Payment amount
            transaction_id: Unique transaction ID
            description: Payment description
        
        Returns:
            Dict containing payment initialization response
        """
        try:
            account = await self.get_active_account()
            if not account:
                return {
                    'success': False,
                    'error': 'No active PayHero account configured'
                }
            
            # Prepare payment request
            payload = {
                'amount': amount,
                'phone_number': self._format_phone_number(phone_number),
                'channel_id': account.shortcode or account.account_number,
                'provider': 'm-pesa',
                'external_reference': transaction_id,
                'callback_url': await self._get_callback_url(),
                'description': description or f"WiFi Bundle - {transaction_id[:8]}"
            }
            
            # Log request
            await self._log_transaction(
                transaction_id=transaction_id,
                request_data=payload,
                status='INITIATED'
            )
            
            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = await self._get_headers(account)
                response = await client.post(
                    f"{self.base_url}/api/v1/payments",
                    json=payload,
                    headers=headers
                )
                
                response_data = response.json()
                
                # Log response
                await self._log_transaction(
                    transaction_id=transaction_id,
                    response_data=response_data,
                    status='SUCCESS' if response.status_code == 200 else 'FAILED',
                    error_message=None if response.status_code == 200 else response_data.get('message')
                )
                
                if response.status_code == 200 and response_data.get('success'):
                    return {
                        'success': True,
                        'payment_reference': response_data.get('reference'),
                        'checkout_request_id': response_data.get('checkout_request_id'),
                        'response_data': response_data
                    }
                else:
                    return {
                        'success': False,
                        'error': response_data.get('message', 'Payment initialization failed'),
                        'response_data': response_data
                    }
                    
        except Exception as e:
            logger.error(f"Error initializing PayHero payment: {str(e)}", exc_info=True)
            await self._log_transaction(
                transaction_id=transaction_id,
                status='ERROR',
                error_message=str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    async def verify_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Verify PayHero payment status.
        
        Args:
            transaction_id: Transaction ID to verify
        
        Returns:
            Dict containing verification response
        """
        try:
            account = await self.get_active_account()
            if not account:
                return {
                    'success': False,
                    'error': 'No active PayHero account configured'
                }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = await self._get_headers(account)
                response = await client.get(
                    f"{self.base_url}/api/v1/payments/{transaction_id}",
                    headers=headers
                )
                
                response_data = response.json()
                
                if response.status_code == 200:
                    return {
                        'success': True,
                        'status': response_data.get('status'),
                        'response_data': response_data
                    }
                else:
                    return {
                        'success': False,
                        'error': response_data.get('message', 'Verification failed'),
                        'response_data': response_data
                    }
                    
        except Exception as e:
            logger.error(f"Error verifying PayHero payment: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def test_connection(self, account_id: int) -> Dict[str, Any]:
        """
        Test connection to PayHero API with given account.
        
        Args:
            account_id: Account ID to test
        
        Returns:
            Dict containing test results
        """
        try:
            result = await self.db.execute(
                select(PaymentGatewayAccount).where(PaymentGatewayAccount.id == account_id)
            )
            account = result.scalar_one_or_none()
            
            if not account:
                return {
                    'success': False,
                    'error': 'Account not found'
                }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = await self._get_headers(account)
                response = await client.get(
                    f"{self.base_url}/api/v1/account/balance",
                    headers=headers
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Update account test status
                    account.last_tested_at = datetime.utcnow()
                    account.last_test_status = 'SUCCESS'
                    await self.db.commit()
                    
                    return {
                        'success': True,
                        'message': 'Connection successful',
                        'balance': response_data.get('balance'),
                        'response_data': response_data
                    }
                else:
                    # Update account test status
                    account.last_tested_at = datetime.utcnow()
                    account.last_test_status = 'FAILED'
                    await self.db.commit()
                    
                    return {
                        'success': False,
                        'error': f'Connection failed: HTTP {response.status_code}',
                        'response_data': response.json()
                    }
                    
        except Exception as e:
            logger.error(f"Error testing PayHero connection: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new PayHero account."""
        try:
            account = PaymentGatewayAccount(
                account_name=account_data.get('account_name'),
                gateway_type='payhero',
                api_key=account_data.get('api_key'),
                api_secret=account_data.get('api_secret'),
                account_number=account_data.get('account_number'),
                business_number=account_data.get('business_number'),
                shortcode=account_data.get('shortcode'),
                passkey=account_data.get('passkey'),
                consumer_key=account_data.get('consumer_key'),
                consumer_secret=account_data.get('consumer_secret'),
                environment=account_data.get('environment', 'sandbox'),
                is_active=account_data.get('is_active', False),
                priority=account_data.get('priority', 0),
                created_by=account_data.get('created_by', 'admin')
            )
            
            # If this is the first account, make it active
            if account_data.get('is_active', False):
                await self._deactivate_other_accounts()
            
            self.db.add(account)
            await self.db.commit()
            await self.db.refresh(account)
            
            return {
                'success': True,
                'account': account.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error creating PayHero account: {str(e)}")
            await self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def update_account(self, account_id: int, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing PayHero account."""
        try:
            result = await self.db.execute(
                select(PaymentGatewayAccount).where(PaymentGatewayAccount.id == account_id)
            )
            account = result.scalar_one_or_none()
            
            if not account:
                return {
                    'success': False,
                    'error': 'Account not found'
                }
            
            # Update fields
            for key, value in account_data.items():
                if hasattr(account, key) and value is not None:
                    setattr(account, key, value)
            
            # Handle activation/deactivation
            if account_data.get('is_active', False):
                await self._deactivate_other_accounts(account_id)
            
            account.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(account)
            
            return {
                'success': True,
                'account': account.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error updating PayHero account: {str(e)}")
            await self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def delete_account(self, account_id: int) -> Dict[str, Any]:
        """Delete a PayHero account."""
        try:
            result = await self.db.execute(
                select(PaymentGatewayAccount).where(PaymentGatewayAccount.id == account_id)
            )
            account = result.scalar_one_or_none()
            
            if not account:
                return {
                    'success': False,
                    'error': 'Account not found'
                }
            
            await self.db.delete(account)
            await self.db.commit()
            
            return {
                'success': True,
                'message': 'Account deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error deleting PayHero account: {str(e)}")
            await self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_all_accounts(self) -> list:
        """Get all PayHero accounts."""
        try:
            result = await self.db.execute(
                select(PaymentGatewayAccount)
                .where(PaymentGatewayAccount.gateway_type == 'payhero')
                .order_by(PaymentGatewayAccount.priority.desc())
            )
            accounts = result.scalars().all()
            return [account.to_dict() for account in accounts]
            
        except Exception as e:
            logger.error(f"Error getting PayHero accounts: {str(e)}")
            return []
    
    async def _deactivate_other_accounts(self, exclude_id: int = None):
        """Deactivate all other PayHero accounts."""
        try:
            query = select(PaymentGatewayAccount).where(
                and_(
                    PaymentGatewayAccount.gateway_type == 'payhero',
                    PaymentGatewayAccount.is_active == True
                )
            )
            
            if exclude_id:
                query = query.where(PaymentGatewayAccount.id != exclude_id)
            
            result = await self.db.execute(query)
            accounts = result.scalars().all()
            
            for account in accounts:
                account.is_active = False
                account.updated_at = datetime.utcnow()
            
            await self.db.flush()
            
        except Exception as e:
            logger.error(f"Error deactivating accounts: {str(e)}")
    
    async def _get_headers(self, account: PaymentGatewayAccount) -> Dict[str, str]:
        """Get API headers for PayHero requests."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        
        # Generate auth token
        auth_string = f"{account.api_key}:{account.api_secret}"
        auth_token = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_token}',
            'Content-Type': 'application/json',
            'X-Timestamp': timestamp,
        }
        
        return headers
    
    async def _get_callback_url(self) -> str:
        """Get the payment callback URL."""
        result = await self.db.execute(
            select(PaymentGatewayConfig).where(
                PaymentGatewayConfig.config_key == 'payhero_callback_url'
            )
        )
        config = result.scalar_one_or_none()
        
        if config:
            return config.config_value
        else:
            return f"{settings.BACKEND_URL}/payment/callback"
    
    async def _log_transaction(
        self,
        transaction_id: str,
        request_data: Dict = None,
        response_data: Dict = None,
        status: str = None,
        error_message: str = None
    ):
        """Log payment gateway transaction."""
        try:
            log = PaymentGatewayLog(
                transaction_id=transaction_id,
                gateway_type='payhero',
                request_data=request_data,
                response_data=response_data,
                status=status,
                error_message=error_message
            )
            self.db.add(log)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging transaction: {str(e)}")
    
    @staticmethod
    def _format_phone_number(phone_number: str) -> str:
        """Format phone number for PayHero API."""
        # Remove spaces and special characters
        phone = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Handle different formats
        if phone.startswith('+254'):
            return phone[1:]  # Remove + sign
        elif phone.startswith('254'):
            return phone
        elif phone.startswith('0'):
            return '254' + phone[1:]  # Replace 0 with 254
        elif phone.startswith('7') or phone.startswith('1'):
            return '254' + phone
        
        return phone
