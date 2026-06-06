from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db, User
from config.security import get_security_settings, verify_password, get_password_hash, create_access_token
from config.limiter import limiter

router = APIRouter()
templates = Jinja2Templates(directory="templates")
settings = get_security_settings()

# get_db, verify_password and create_access_token are imported from shared modules

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, message: str = None):
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "message": message
        }
    )

@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "message": "Invalid username or password"
            },
            status_code=401
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "message": "User account is inactive"
            },
            status_code=401
        )

    access_token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role
        }
    )

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE
    )
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response
