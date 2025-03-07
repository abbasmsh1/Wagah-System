from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from database import SessionLocal, User
from typing import Optional
from datetime import datetime
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-keep-it-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    async def __call__(self, request: Request, token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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