from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from database import SessionLocal, User
from typing import Optional
from datetime import datetime
from config.security import get_security_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
settings = get_security_settings()

async def get_token_from_cookie(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        return token[7:]  # Remove "Bearer " prefix
    return None

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    async def __call__(self, request: Request):
        token = await get_token_from_cookie(request)
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid authentication token")
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    raise HTTPException(status_code=401, detail="User not found")
                
                if user.role not in self.allowed_roles:
                    raise HTTPException(
                        status_code=403, 
                        detail="You don't have sufficient permissions to perform this action"
                    )
                
                # Add user info to request state
                request.state.user = user
                request.state.is_admin = user.role == "admin"
                
            finally:
                db.close()
                
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        return True

# Create role checker instances
admin_required = RoleChecker(["admin"])
staff_required = RoleChecker(["admin", "staff"])
user_required = RoleChecker(["admin", "staff", "user"]) 