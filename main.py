import warnings

warnings.filterwarnings("ignore")

import logging
import os
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
from passlib.context import CryptContext
from pydantic import BaseModel
from fpdf import FPDF
import xlsxwriter

from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Bus, Plane, Train, ProcessedMaster, User
from routers import master, transport, booking, admin, auth
from middleware.auth import user_required
from config.security import get_security_settings, get_security_headers

# Create FastAPI app
app = FastAPI(title="Wagah System")

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

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Token functions
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# Include routers
app.include_router(auth.router, tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(master.router, prefix="/master", tags=["master"])
app.include_router(transport.router, prefix="/transport", tags=["transport"])
app.include_router(booking.router, prefix="/booking", tags=["booking"])

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
            hashed_password = get_password_hash("admin")
            admin_user = User(
                username="admin",
                hashed_password=hashed_password,
                role="admin",
                designation="System Administrator",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created initial admin user")
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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
