from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def generate_csrf_token() -> str:
    """Generate a random token for the double-submit CSRF cookie."""
    return secrets.token_urlsafe(32)

class SecuritySettings(BaseSettings):
    # Security
    # Required: no default, so the app refuses to start without an explicit
    # SECRET_KEY and can never silently run on a public/hardcoded key.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application
    DEBUG: bool = False
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Cookie
    COOKIE_SECURE: bool = True
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "Lax"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Password
    MIN_PASSWORD_LENGTH: int = 8

    class Config:
        case_sensitive = True
        # Load .env directly so settings don't depend on some other module
        # having called load_dotenv() first (import-order independence).
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_security_settings() -> SecuritySettings:
    return SecuritySettings()

def create_access_token(data: dict) -> str:
    """Encode a signed JWT access token with an expiry claim."""
    settings = get_security_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# Security Policy Configuration
security_policies = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"],
    "style-src": ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"],
    "img-src": ["'self'", "data:", "ui-avatars.com"],
    "font-src": ["'self'", "cdn.jsdelivr.net"],
    "connect-src": ["'self'"],
    "frame-ancestors": ["'none'"],
    "form-action": ["'self'"],
    "base-uri": ["'self'"],
    "object-src": ["'none'"]
}

def get_security_headers():
    """Return security headers to be used in responses"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "; ".join(
            f"{key} {' '.join(values)}"
            for key, values in security_policies.items()
        ),
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
    }

def validate_password(password: str) -> bool:
    """Validate password against security requirements"""
    settings = get_security_settings()
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False

    # Check for at least one uppercase letter
    if not any(c.isupper() for c in password):
        return False

    # Check for at least one lowercase letter
    if not any(c.islower() for c in password):
        return False

    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        return False

    # Check for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False

    return True
