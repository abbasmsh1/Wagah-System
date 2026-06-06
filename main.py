import warnings

warnings.filterwarnings("ignore")

import logging
import os
import secrets
from datetime import datetime, timedelta, date, time
from typing import List, Optional
import json
import csv
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Depends, Request, Form, HTTPException, File, UploadFile, APIRouter, WebSocket
from fastapi import Query, Path
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, text, or_, and_, Date
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.websockets import WebSocketDisconnect
from jose import JWTError, jwt
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from config.limiter import limiter
from fpdf import FPDF
import xlsxwriter

from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Bus, Plane, Train, ProcessedMaster, User
from routers import master, transport, booking, admin, auth
from middleware.auth import user_required
from config.security import get_security_settings, get_security_headers, verify_password, get_password_hash, generate_csrf_token

# Create FastAPI app
app = FastAPI(title="Wagah System")

# Rate limiting (slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Get security settings
settings = get_security_settings()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Add custom auth state middleware
from middleware.session import AuthStateMiddleware
app.add_middleware(AuthStateMiddleware)

# Attach security headers (CSP, HSTS, X-Frame-Options, ...) to every response,
# and issue the CSRF double-submit cookie when one isn't present yet.
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in get_security_headers().items():
        response.headers[header] = value
    if not request.cookies.get("csrf_token"):
        response.set_cookie(
            key="csrf_token",
            value=generate_csrf_token(),
            max_age=settings.SESSION_EXPIRE_MINUTES * 60,
            samesite=settings.COOKIE_SAMESITE.lower(),
            secure=settings.COOKIE_SECURE,
            httponly=False,  # readable by JS so forms can echo it back
        )
    return response

# Password hashing context moved to config.security

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Password hashing functions
# Password hashing functions are imported from config.security

# Token functions
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# Include routers (CSRF dependency guards all state-changing POSTs;
# it is a no-op for safe methods like GET)
from middleware.csrf import csrf_protect
app.include_router(auth.router, tags=["auth"], dependencies=[Depends(csrf_protect)])
app.include_router(admin.router, prefix="/admin", tags=["admin"], dependencies=[Depends(csrf_protect)])
app.include_router(master.router, prefix="/master", tags=["master"], dependencies=[Depends(csrf_protect)])
app.include_router(transport.router, prefix="/transport", tags=["transport"], dependencies=[Depends(csrf_protect)])
app.include_router(booking.router, prefix="/booking", tags=["booking"], dependencies=[Depends(csrf_protect)])

# Error handlers -- render friendly HTML pages instead of raw JSON, and send
# unauthenticated users to the login page.
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        return RedirectResponse(url="/login", status_code=303)
    if exc.status_code == 403:
        return templates.TemplateResponse(
            "errors/403.html",
            {"request": request, "error_title": "Access Denied",
             "error_message": exc.detail or "You do not have permission to access this page."},
            status_code=403,
        )
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {"request": request, "error_title": "Page Not Found",
             "error_message": exc.detail or "The page you are looking for does not exist."},
            status_code=404,
        )
    # Other client errors keep a simple JSON detail.
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error processing %s %s", request.method, request.url.path)
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request, "error_title": "Server Error",
         "error_message": "An unexpected error occurred. Please try again later."},
        status_code=500,
    )

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_year": datetime.now().year
        }
    )

# Create initial admin user if no users exist
def create_initial_admin():
    db = SessionLocal()
    try:
        user_count = db.query(func.count(User.id)).scalar()
        if user_count == 0:
            username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
            password = os.getenv("INITIAL_ADMIN_PASSWORD")
            generated = not password  # treat unset or empty as "generate one"
            if generated:
                # No weak hardcoded default: generate a strong random password.
                password = secrets.token_urlsafe(16)
            admin_user = User(
                username=username,
                hashed_password=get_password_hash(password),
                role="admin",
                designation="System Administrator",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            if generated:
                logger.warning(
                    "Created initial admin '%s' with a GENERATED password: %s "
                    "-- log in and change it immediately.", username, password
                )
            else:
                logger.info("Created initial admin '%s' from INITIAL_ADMIN_PASSWORD.", username)
    except Exception as e:
        logger.error(f"Error creating initial admin user: {e}")
    finally:
        db.close()

# Create initial admin user on startup
@app.on_event("startup")
async def startup_event():
    create_initial_admin()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
