"""
Lincoln's net - Admin Authentication
HTTP Basic Authentication for Admin Panel
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config.settings import settings
import secrets
import logging

logger = logging.getLogger(__name__)

# HTTP Basic Authentication
security = HTTPBasic()


def verify_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """
    Verify admin credentials using HTTP Basic Authentication.
    Uses constant-time comparison to prevent timing attacks.
    """
    correct_username = settings.ADMIN_USERNAME.encode('utf-8')
    correct_password = settings.ADMIN_PASSWORD.encode('utf-8')
    
    provided_username = credentials.username.encode('utf-8')
    provided_password = credentials.password.encode('utf-8')
    
    # Use secrets.compare_digest for constant-time comparison
    is_username_correct = secrets.compare_digest(provided_username, correct_username)
    is_password_correct = secrets.compare_digest(provided_password, correct_password)
    
    if not (is_username_correct and is_password_correct):
        logger.warning(f"Failed admin login attempt from {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    logger.info(f"Admin login successful: {credentials.username}")
    return True


def get_admin_session(authenticated: bool = Depends(verify_admin_credentials)) -> bool:
    """
    Dependency to protect admin routes.
    """
    return authenticated
