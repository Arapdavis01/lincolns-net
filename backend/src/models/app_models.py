"""
Lincoln's net - Application Models
Database models for core application
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    Numeric, ForeignKey, DECIMAL
)
from sqlalchemy.sql import func
from config.database import Base
from datetime import datetime


class InternetPackage(Base):
    """Internet package model."""
    __tablename__ = 'internet_packages'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(DECIMAL(10, 2), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    download_rate_limit = Column(String(50), default='1M')
    upload_rate_limit = Column(String(50), default='1M')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price) if self.price else 0,
            'duration_seconds': self.duration_seconds,
            'download_rate_limit': self.download_rate_limit,
            'upload_rate_limit': self.upload_rate_limit,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BillingTransaction(Base):
    """Billing transaction model."""
    __tablename__ = 'billing_transactions'
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(36), unique=True, nullable=False)
    phone_number = Column(String(20), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    mac_address = Column(String(17), nullable=False)
    package_id = Column(Integer, ForeignKey('internet_packages.id'))
    status = Column(String(20), default='PENDING')
    payment_reference = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'phone_number': self.phone_number,
            'amount': float(self.amount) if self.amount else 0,
            'mac_address': self.mac_address,
            'package_id': self.package_id,
            'status': self.status,
            'payment_reference': self.payment_reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class SystemSetting(Base):
    """System setting model."""
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(255), unique=True, nullable=False)
    setting_value = Column(Text)
    description = Column(Text)
    is_secret = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'description': self.description,
            'is_secret': self.is_secret,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
