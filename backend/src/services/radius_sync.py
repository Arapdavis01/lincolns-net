"""
Lincoln's net - RADIUS Synchronization Service
Handles RADIUS database synchronization for authenticated users
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, insert, select
from config.database import AsyncSessionLocal
from datetime import datetime, timedelta
import logging
import hashlib
import secrets

logger = logging.getLogger(__name__)


async def sync_to_radius(
    mac_address: str,
    duration_seconds: int,
    download_rate: str,
    upload_rate: str
) -> bool:
    """
    Synchronize user authentication data to FreeRADIUS tables.
    
    Args:
        mac_address: MAC address of the client device
        duration_seconds: Session duration in seconds
        download_rate: Download rate limit (e.g., "5M")
        upload_rate: Upload rate limit (e.g., "2M")
    
    Returns:
        bool: True if sync successful, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            # Clean up any existing RADIUS entries for this MAC
            await session.execute(
                delete(RadCheck).where(RadCheck.username == mac_address)
            )
            await session.execute(
                delete(RadReply).where(RadReply.username == mac_address)
            )
            
            # Generate password based on MAC address
            password = generate_radius_password(mac_address)
            
            # Add RADIUS check entry (authentication)
            session.add(RadCheck(
                username=mac_address,
                attribute='Cleartext-Password',
                op=':=',
                value=password
            ))
            
            # Add RADIUS reply entries (authorization)
            # Session timeout
            session.add(RadReply(
                username=mac_address,
                attribute='Session-Timeout',
                op='=',
                value=str(duration_seconds)
            ))
            
            # MikroTik rate limit for bandwidth control
            rate_limit = f"{download_rate}/{upload_rate}"
            session.add(RadReply(
                username=mac_address,
                attribute='Mikrotik-Rate-Limit',
                op='=',
                value=rate_limit
            ))
            
            # MikroTik total limit
            session.add(RadReply(
                username=mac_address,
                attribute='Mikrotik-Total-Limit',
                op='=',
                value=str(duration_seconds)
            ))
            
            # Add idle timeout to prevent lingering sessions
            session.add(RadReply(
                username=mac_address,
                attribute='Idle-Timeout',
                op='=',
                value='300'
            ))
            
            # Set session termination action
            session.add(RadReply(
                username=mac_address,
                attribute='Session-Terminate-Action',
                op='=',
                value='RADIUS-Request'
            ))
            
            await session.commit()
            
            logger.info(f"RADIUS sync successful for MAC: {mac_address}")
            return True
            
    except Exception as e:
        logger.error(f"RADIUS sync failed for MAC {mac_address}: {str(e)}", exc_info=True)
        return False


async def remove_from_radius(mac_address: str) -> bool:
    """
    Remove user from RADIUS database (for expired sessions).
    
    Args:
        mac_address: MAC address of the client device
    
    Returns:
        bool: True if removal successful, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            # Delete RADIUS check entries
            await session.execute(
                delete(RadCheck).where(RadCheck.username == mac_address)
            )
            
            # Delete RADIUS reply entries
            await session.execute(
                delete(RadReply).where(RadReply.username == mac_address)
            )
            
            await session.commit()
            
            logger.info(f"RADIUS removal successful for MAC: {mac_address}")
            return True
            
    except Exception as e:
        logger.error(f"RADIUS removal failed for MAC {mac_address}: {str(e)}", exc_info=True)
        return False


async def cleanup_expired_sessions() -> int:
    """
    Clean up expired RADIUS sessions.
    Called periodically to remove expired users.
    
    Returns:
        int: Number of sessions cleaned up
    """
    try:
        async with AsyncSessionLocal() as session:
            # Find expired RADIUS entries
            # This is a simplified version - in production, you'd check
            # the actual session expiration times
            result = await session.execute(
                select(RadReply).where(
                    RadReply.attribute == 'Session-Timeout',
                    RadReply.value < datetime.utcnow().isoformat()
                )
            )
            expired_entries = result.scalars().all()
            
            cleanup_count = 0
            for entry in expired_entries:
                await remove_from_radius(entry.username)
                cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} expired RADIUS sessions")
            return cleanup_count
            
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {str(e)}", exc_info=True)
        return 0


def generate_radius_password(mac_address: str) -> str:
    """
    Generate a secure password for RADIUS authentication.
    
    Args:
        mac_address: MAC address of the client device
    
    Returns:
        str: Generated password
    """
    # Create a deterministic but secure password based on MAC address
    mac_normalized = mac_address.lower().replace(':', '').replace('-', '')
    
    # Add salt for security
    salt = "lincolnsnet_2024"
    
    # Generate hash
    hash_obj = hashlib.sha256(f"{mac_normalized}_{salt}".encode('utf-8'))
    password = hash_obj.hexdigest()[:16]
    
    return password


class RadCheck:
    """RADIUS Check table model."""
    __tablename__ = 'radcheck'
    
    def __init__(self, username, attribute, op, value):
        self.username = username
        self.attribute = attribute
        self.op = op
        self.value = value


class RadReply:
    """RADIUS Reply table model."""
    __tablename__ = 'radreply'
    
    def __init__(self, username, attribute, op, value):
        self.username = username
        self.attribute = attribute
        self.op = op
        self.value = value
