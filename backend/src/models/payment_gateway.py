"""
Lincoln's net - Payment Gateway Models
Database models for PayHero/Safaricom configuration
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, JSON, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base
from datetime import datetime


class PaymentGatewayAccount(Base):
    """Payment gateway account configuration model."""
    __tablename__ = 'payment_gateway_accounts'
    
    id = Column(Integer, primary_key=True, index=True)
    account_name = Column(String(255), nullable=False, unique=True)
    gateway_type = Column(String(50), nullable=False, default='payhero')
    api_key = Column(String(255))
    api_secret = Column(String(255))
    account_number = Column(String(100))
    business_number = Column(String(100))
    shortcode = Column(String(50))
    passkey = Column(String(255))
    consumer_key = Column(String(255))
    consumer_secret = Column(String(255))
    environment = Column(String(20), default='sandbox')
    is_active = Column(Boolean, default=False)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_tested_at = Column(DateTime(timezone=True))
    last_test_status = Column(String(20))
    created_by = Column(String(255))
    
    def to_dict(self, include_secrets=False):
        """Convert to dictionary, optionally including secret fields."""
        data = {
            'id': self.id,
            'account_name': self.account_name,
            'gateway_type': self.gateway_type,
            'account_number': self.account_number,
            'business_number': self.business_number,
            'shortcode': self.shortcode,
            'environment': self.environment,
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_tested_at': self.last_tested_at.isoformat() if self.last_tested_at else None,
            'last_test_status': self.last_test_status,
        }
        
        if include_secrets:
            data.update({
                'api_key': self.api_key,
                'api_secret': self.api_secret,
                'passkey': self.passkey,
                'consumer_key': self.consumer_key,
                'consumer_secret': self.consumer_secret,
            })
        
        return data


class PaymentGatewayConfig(Base):
    """Payment gateway configuration settings."""
    __tablename__ = 'payment_gateway_config'
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(255), unique=True, nullable=False)
    config_value = Column(Text)
    description = Column(Text)
    gateway_type = Column(String(50), default='payhero')
    is_encrypted = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'description': self.description,
            'gateway_type': self.gateway_type,
            'is_encrypted': self.is_encrypted,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentGatewayLog(Base):
    """Payment gateway transaction logs."""
    __tablename__ = 'payment_gateway_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(36), index=True)
    gateway_type = Column(String(50))
    request_data = Column(JSON)
    response_data = Column(JSON)
    status = Column(String(20))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'gateway_type': self.gateway_type,
            'request_data': self.request_data,
            'response_data': self.response_data,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
