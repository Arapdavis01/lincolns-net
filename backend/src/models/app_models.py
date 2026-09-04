"""
Lincoln's net - Application Models
Database models for core application
Includes InternetPackage, BillingTransaction, and SystemSetting
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    Numeric, ForeignKey, DECIMAL, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid


class InternetPackage(Base):
    """
    Internet package model.
    Represents WiFi bundles available for purchase.
    """
    __tablename__ = 'internet_packages'
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Package Information
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Pricing (in KES)
    price = Column(DECIMAL(10, 2), nullable=False)
    
    # Duration and Bandwidth
    duration_seconds = Column(Integer, nullable=False)
    download_rate_limit = Column(String(50), default='1M', nullable=False)
    upload_rate_limit = Column(String(50), default='1M', nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    transactions = relationship("BillingTransaction", back_populates="package")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('duration_seconds > 0', name='check_duration_positive'),
        Index('idx_internet_packages_active', 'is_active'),
        Index('idx_internet_packages_price', 'price'),
    )
    
    def to_dict(self, include_transactions: bool = False) -> Dict[str, Any]:
        """
        Convert package to dictionary.
        
        Args:
            include_transactions: Whether to include related transactions
        
        Returns:
            Dictionary representation of the package
        """
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price) if self.price else 0,
            'price_display': f"KES {float(self.price):,.2f}" if self.price else "KES 0.00",
            'duration_seconds': self.duration_seconds,
            'duration_display': self.format_duration(self.duration_seconds),
            'download_rate_limit': self.download_rate_limit,
            'upload_rate_limit': self.upload_rate_limit,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_transactions:
            data['transactions'] = [t.to_dict() for t in self.transactions]
        
        return data
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format duration in seconds to human-readable string."""
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
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<InternetPackage(id={self.id}, name='{self.name}', price=KES {self.price})>"


class BillingTransaction(Base):
    """
    Billing transaction model.
    Represents customer payment transactions.
    """
    __tablename__ = 'billing_transactions'
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction Information
    transaction_id = Column(
        String(36), 
        unique=True, 
        nullable=False, 
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    phone_number = Column(String(20), nullable=False, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    mac_address = Column(String(17), nullable=False, index=True)
    
    # Foreign Key
    package_id = Column(
        Integer, 
        ForeignKey('internet_packages.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # Status and Payment
    status = Column(
        String(20), 
        default='PENDING', 
        nullable=False,
        index=True
    )
    payment_reference = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    package = relationship("InternetPackage", back_populates="transactions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_transaction_amount_positive'),
        CheckConstraint(
            "status IN ('PENDING', 'SUCCESS', 'FAILED', 'EXPIRED')",
            name='check_transaction_status_valid'
        ),
        Index('idx_billing_transactions_mac', 'mac_address'),
        Index('idx_billing_transactions_status', 'status'),
        Index('idx_billing_transactions_created', 'created_at'),
        Index('idx_billing_transactions_expires', 'expires_at'),
    )
    
    # Valid statuses
    VALID_STATUSES = ['PENDING', 'SUCCESS', 'FAILED', 'EXPIRED']
    
    def to_dict(self, include_package: bool = False) -> Dict[str, Any]:
        """
        Convert transaction to dictionary.
        
        Args:
            include_package: Whether to include related package
        
        Returns:
            Dictionary representation of the transaction
        """
        data = {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'phone_number': self.phone_number,
            'amount': float(self.amount) if self.amount else 0,
            'amount_display': f"KES {float(self.amount):,.2f}" if self.amount else "KES 0.00",
            'mac_address': self.mac_address,
            'package_id': self.package_id,
            'status': self.status,
            'payment_reference': self.payment_reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired() if self.expires_at else False,
            'is_active': self.is_active() if self.expires_at else False,
        }
        
        if include_package and self.package:
            data['package'] = self.package.to_dict()
        
        return data
    
    def is_expired(self) -> bool:
        """Check if transaction has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_active(self) -> bool:
        """Check if transaction is currently active."""
        return (
            self.status == 'SUCCESS' 
            and self.expires_at is not None 
            and not self.is_expired()
        )
    
    def mark_success(self, payment_reference: Optional[str] = None):
        """Mark transaction as successful."""
        self.status = 'SUCCESS'
        if payment_reference:
            self.payment_reference = payment_reference
    
    def mark_failed(self, reason: Optional[str] = None):
        """Mark transaction as failed."""
        self.status = 'FAILED'
        if reason:
            self.payment_reference = reason
    
    def mark_expired(self):
        """Mark transaction as expired."""
        self.status = 'EXPIRED'
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<BillingTransaction(id={self.id}, phone='{self.phone_number}', amount=KES {self.amount}, status='{self.status}')>"


class SystemSetting(Base):
    """
    System setting model.
    Stores configuration key-value pairs.
    """
    __tablename__ = 'system_settings'
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Setting Information
    setting_key = Column(String(255), unique=True, nullable=False, index=True)
    setting_value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    def to_dict(self, include_secret: bool = False) -> Dict[str, Any]:
        """
        Convert setting to dictionary.
        
        Args:
            include_secret: Whether to include secret values
        
        Returns:
            Dictionary representation of the setting
        """
        # Don't expose secret values unless explicitly requested
        if self.is_secret and not include_secret:
            return {
                'id': self.id,
                'setting_key': self.setting_key,
                'setting_value': '[HIDDEN]',
                'description': self.description,
                'is_secret': self.is_secret,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }
        
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'description': self.description,
            'is_secret': self.is_secret,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return f"<SystemSetting(key='{self.setting_key}', secret={self.is_secret})>"


# ============================================================================
# Helper Functions
# ============================================================================

def create_default_packages() -> list:
    """
    Create default internet packages.
    Returns list of InternetPackage objects.
    """
    return [
        InternetPackage(
            name='Hourly Pass',
            description='1 hour of high-speed internet access',
            price=100.00,
            duration_seconds=3600,
            download_rate_limit='5M',
            upload_rate_limit='2M',
        ),
        InternetPackage(
            name='Daily Pass',
            description='24 hours of unlimited internet access',
            price=300.00,
            duration_seconds=86400,
            download_rate_limit='10M',
            upload_rate_limit='5M',
        ),
        InternetPackage(
            name='Weekly Pass',
            description='7 days of premium internet access',
            price=1500.00,
            duration_seconds=604800,
            download_rate_limit='20M',
            upload_rate_limit='10M',
        ),
        InternetPackage(
            name='Monthly Pass',
            description='30 days of unlimited internet access',
            price=5000.00,
            duration_seconds=2592000,
            download_rate_limit='50M',
            upload_rate_limit='25M',
        ),
    ]


def create_default_settings() -> list:
    """
    Create default system settings.
    Returns list of SystemSetting objects.
    """
    return [
        SystemSetting(
            setting_key='gateway_name',
            setting_value="Lincoln's net",
            description='WiFi Gateway Name',
            is_secret=False,
        ),
        SystemSetting(
            setting_key='currency',
            setting_value='KES',
            description='Currency Code',
            is_secret=False,
        ),
        SystemSetting(
            setting_key='timezone',
            setting_value='Africa/Nairobi',
            description='System Timezone',
            is_secret=False,
        ),
        SystemSetting(
            setting_key='admin_email',
            setting_value='admin@lincolnsnet.com',
            description='Administrator Email',
            is_secret=False,
        ),
        SystemSetting(
            setting_key='support_phone',
            setting_value='+254700000000',
            description='Support Phone Number',
            is_secret=False,
        ),
        SystemSetting(
            setting_key='radius_secret',
            setting_value='change-this-secret-key',
            description='RADIUS Server Secret',
            is_secret=True,
        ),
    ]


# ============================================================================
# Export Models
# ============================================================================

__all__ = [
    'InternetPackage',
    'BillingTransaction',
    'SystemSetting',
    'create_default_packages',
    'create_default_settings',
]
