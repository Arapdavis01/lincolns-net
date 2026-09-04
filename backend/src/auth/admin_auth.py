"""
Lincoln's net - Admin Authentication
Custom Login Page with HTTP Basic Authentication and Session Management
"""

from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from config.settings import settings
import secrets
import logging
import base64
import hashlib
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# HTTP Basic Authentication
security = HTTPBasic()

# Templates configuration
templates = Jinja2Templates(directory="templates")

# Simple in-memory session store (for production, use Redis or database)
# Format: {session_token: {"username": str, "expires_at": datetime}}
admin_sessions: Dict[str, Dict] = {}

# Session timeout (in minutes)
SESSION_TIMEOUT_MINUTES = 30

# Maximum failed login attempts before temporary lockout
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

# Track failed login attempts
failed_attempts: Dict[str, list] = {}


class AdminAuthManager:
    """Admin authentication manager with session handling."""
    
    def __init__(self):
        self.security = HTTPBasic()
        self.sessions = admin_sessions
        self.session_timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """
        Verify admin credentials using constant-time comparison.
        Prevents timing attacks.
        """
        correct_username = settings.ADMIN_USERNAME.encode('utf-8')
        correct_password = settings.ADMIN_PASSWORD.encode('utf-8')
        
        provided_username = username.encode('utf-8')
        provided_password = password.encode('utf-8')
        
        # Use secrets.compare_digest for constant-time comparison
        is_username_correct = secrets.compare_digest(provided_username, correct_username)
        is_password_correct = secrets.compare_digest(provided_password, correct_password)
        
        return is_username_correct and is_password_correct
    
    def check_rate_limit(self, ip_address: str) -> bool:
        """
        Check if the IP address has exceeded failed login attempts.
        Returns True if login is allowed, False if locked out.
        """
        if ip_address not in failed_attempts:
            return True
        
        # Clean up old attempts
        current_time = datetime.utcnow()
        recent_attempts = [
            attempt_time for attempt_time in failed_attempts[ip_address]
            if current_time - attempt_time < timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        ]
        failed_attempts[ip_address] = recent_attempts
        
        # Check if locked out
        if len(recent_attempts) >= MAX_FAILED_ATTEMPTS:
            return False
        
        return True
    
    def record_failed_attempt(self, ip_address: str):
        """Record a failed login attempt for rate limiting."""
        if ip_address not in failed_attempts:
            failed_attempts[ip_address] = []
        failed_attempts[ip_address].append(datetime.utcnow())
    
    def create_session(self, username: str) -> str:
        """Create a new admin session and return session token."""
        # Generate secure session token
        session_token = secrets.token_urlsafe(32)
        
        # Store session
        self.sessions[session_token] = {
            "username": username,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + self.session_timeout,
        }
        
        # Clean up expired sessions
        self.cleanup_expired_sessions()
        
        return session_token
    
    def validate_session(self, session_token: str) -> bool:
        """Validate if a session token is still valid."""
        if session_token not in self.sessions:
            return False
        
        session = self.sessions[session_token]
        if datetime.utcnow() > session["expires_at"]:
            del self.sessions[session_token]
            return False
        
        # Extend session on activity
        session["expires_at"] = datetime.utcnow() + self.session_timeout
        return True
    
    def get_session_username(self, session_token: str) -> Optional[str]:
        """Get username associated with a session token."""
        if self.validate_session(session_token):
            return self.sessions[session_token]["username"]
        return None
    
    def invalidate_session(self, session_token: str):
        """Invalidate a session (logout)."""
        if session_token in self.sessions:
            del self.sessions[session_token]
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions from memory."""
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, session in self.sessions.items()
            if current_time > session["expires_at"]
        ]
        for token in expired_tokens:
            del self.sessions[token]


# Create auth manager instance
auth_manager = AdminAuthManager()


def verify_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """
    Verify admin credentials using HTTP Basic Authentication.
    Uses constant-time comparison to prevent timing attacks.
    """
    is_valid = auth_manager.verify_credentials(
        credentials.username,
        credentials.password
    )
    
    if not is_valid:
        logger.warning(f"Failed admin login attempt for username: {credentials.username}")
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


def get_admin_session_cookie(request: Request) -> Optional[str]:
    """Get admin session from cookie."""
    return request.cookies.get("admin_session")


def require_admin_session(request: Request) -> bool:
    """
    Check if admin has valid session cookie.
    Returns True if session is valid, False otherwise.
    """
    session_token = request.cookies.get("admin_session")
    if not session_token:
        return False
    
    return auth_manager.validate_session(session_token)


def create_admin_session_response(username: str, redirect_url: str = "/admin/dashboard") -> Response:
    """
    Create response with admin session cookie.
    """
    session_token = auth_manager.create_session(username)
    
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="admin_session",
        value=session_token,
        httponly=True,
        secure=True,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=SESSION_TIMEOUT_MINUTES * 60,
    )
    
    return response


def clear_admin_session_response(redirect_url: str = "/admin/login") -> Response:
    """
    Clear admin session cookie (logout).
    """
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("admin_session")
    return response


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for proxy headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def verify_admin_login(
    request: Request,
    username: str,
    password: str,
    ip_address: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Complete admin login verification with rate limiting.
    
    Returns:
        Tuple of (success, message)
    """
    if ip_address is None:
        ip_address = get_client_ip(request)
    
    # Check rate limiting
    if not auth_manager.check_rate_limit(ip_address):
        logger.warning(f"Admin login blocked due to rate limiting for IP: {ip_address}")
        return False, "Too many failed attempts. Please try again later."
    
    # Verify credentials
    if auth_manager.verify_credentials(username, password):
        # Successful login
        logger.info(f"Admin login successful for user: {username} from IP: {ip_address}")
        return True, "Login successful"
    else:
        # Failed login
        auth_manager.record_failed_attempt(ip_address)
        logger.warning(f"Failed admin login for user: {username} from IP: {ip_address}")
        return False, "Invalid username or password"


def hash_password(password: str) -> str:
    """
    Hash password using SHA-256 (for storage comparison only).
    Note: In production, use bcrypt or argon2 for password hashing.
    """
    salt = settings.SECRET_KEY.encode('utf-8')
    password_hash = hashlib.sha256(salt + password.encode('utf-8')).hexdigest()
    return password_hash


def verify_password_hash(password: str, password_hash: str) -> bool:
    """
    Verify password against stored hash.
    """
    return secrets.compare_digest(
        hash_password(password),
        password_hash
    )


def decode_basic_auth(auth_header: str) -> Tuple[str, str]:
    """
    Decode Basic Authentication header.
    Returns (username, password) tuple.
    """
    try:
        # Remove "Basic " prefix
        encoded = auth_header[6:]
        decoded = base64.b64decode(encoded).decode('utf-8')
        username, password = decoded.split(':', 1)
        return username, password
    except Exception as e:
        logger.error(f"Error decoding Basic Auth: {str(e)}")
        return "", ""


def encode_basic_auth(username: str, password: str) -> str:
    """
    Encode username and password for Basic Authentication.
    """
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return f"Basic {encoded}"


def get_admin_from_request(request: Request) -> Optional[str]:
    """
    Get admin username from request (session or Basic Auth).
    """
    # Check session cookie first
    session_token = request.cookies.get("admin_session")
    if session_token:
        username = auth_manager.get_session_username(session_token)
        if username:
            return username
    
    # Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic "):
        username, password = decode_basic_auth(auth_header)
        if auth_manager.verify_credentials(username, password):
            return username
    
    return None


class AdminSessionMiddleware:
    """
    Middleware to check admin session on protected routes.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope)
        path = request.url.path
        
        # Check if path is admin protected
        if path.startswith("/admin") and path != "/admin/login" and path != "/admin/api/login":
            # Check session
            session_token = request.cookies.get("admin_session")
            if not session_token or not auth_manager.validate_session(session_token):
                # Check Basic Auth header
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Basic "):
                    # Redirect to login page
                    response = RedirectResponse(url="/admin/login", status_code=302)
                    await response(scope, receive, send)
                    return
                
                # Verify Basic Auth
                username, password = decode_basic_auth(auth_header)
                if not auth_manager.verify_credentials(username, password):
                    response = JSONResponse(
                        status_code=401,
                        content={"detail": "Unauthorized"}
                    )
                    await response(scope, receive, send)
                    return
        
        await self.app(scope, receive, send)


# Export all functions and classes
__all__ = [
    'AdminAuthManager',
    'auth_manager',
    'security',
    'templates',
    'verify_admin_credentials',
    'get_admin_session',
    'get_admin_session_cookie',
    'require_admin_session',
    'create_admin_session_response',
    'clear_admin_session_response',
    'get_client_ip',
    'verify_admin_login',
    'hash_password',
    'verify_password_hash',
    'decode_basic_auth',
    'encode_basic_auth',
    'get_admin_from_request',
    'AdminSessionMiddleware',
]
