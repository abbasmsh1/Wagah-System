from pydantic_settings import BaseSettings
from typing import List
import os
from functools import lru_cache

class SecuritySettings(BaseSettings):
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "iGmPib9h7QjNPXfSkWjRJXfi8MeG7f8x0wYxIRkllVA")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Application
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ALLOWED_HOSTS: List[str] = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    
    # Cookie
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "True").lower() == "true"
    COOKIE_HTTPONLY: bool = os.getenv("COOKIE_HTTPONLY", "True").lower() == "true"
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "Lax")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Password
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "15"))
    
    # Session
    SESSION_EXPIRE_MINUTES: int = int(os.getenv("SESSION_EXPIRE_MINUTES", "120"))

    class Config:
        case_sensitive = True

@lru_cache()
def get_security_settings() -> SecuritySettings:
    return SecuritySettings()

# Security Policy Configuration
security_policies = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "cdn.jsdelivr.net"],
    "style-src": ["'self'", "cdn.jsdelivr.net"],
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