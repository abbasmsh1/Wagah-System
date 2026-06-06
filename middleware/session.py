
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from jose import jwt
from database import SessionLocal, User
from .auth import get_token_from_cookie, settings

class AuthStateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Default state
            request.state.user = None
            request.state.is_admin = False
            
            token = await get_token_from_cookie(request)
            if token:
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    username = payload.get("sub")
                    if username:
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.username == username).first()
                            if user:
                                request.state.user = user
                                request.state.is_admin = (user.role == "admin")
                        finally:
                            db.close()
                except Exception:
                    # Invalid token, just ignore and leave user as None
                    pass

            response = await call_next(request)
            return response
        except Exception as e:
            import traceback
            with open("middleware_error.txt", "w") as f:
                f.write(traceback.format_exc())
            raise e
