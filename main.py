import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from config.limiter import limiter

from database import SessionLocal, User, get_db, init_db
from routers import master, transport, booking, admin, auth
from middleware.auth import staff_required
from config.security import get_security_settings, get_security_headers, get_password_hash, generate_csrf_token

# Get security settings
settings = get_security_settings()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic (`alembic upgrade head`). AUTO_CREATE_TABLES
    # is for environments where migrations can't run before boot (e.g. Vercel's
    # ephemeral /tmp SQLite); startup then creates missing tables directly.
    if os.getenv("AUTO_CREATE_TABLES", "").lower() == "true":
        init_db()
    create_initial_admin()
    yield

# Create FastAPI app -- hide interactive docs/openapi unless DEBUG is enabled
app = FastAPI(
    title="Wagah System",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Rate limiting (slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite=settings.COOKIE_SAMESITE.lower(),
            secure=settings.COOKIE_SECURE,
            httponly=False,  # readable by JS so forms can echo it back
        )
    return response

# Password hashing context moved to config.security

# get_db lives in database.py; create_access_token in config.security

# Include routers (CSRF dependency guards all state-changing POSTs;
# it is a no-op for safe methods like GET)
from middleware.csrf import csrf_protect
app.include_router(auth.router, tags=["auth"], dependencies=[Depends(csrf_protect)])
app.include_router(admin.router, prefix="/admin", tags=["admin"], dependencies=[Depends(csrf_protect)])
app.include_router(master.router, prefix="/master", tags=["master"], dependencies=[Depends(csrf_protect), Depends(staff_required)])
app.include_router(transport.router, prefix="/transport", tags=["transport"], dependencies=[Depends(csrf_protect), Depends(staff_required)])
app.include_router(booking.router, prefix="/booking", tags=["booking"], dependencies=[Depends(csrf_protect), Depends(staff_required)])

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

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    """Liveness/readiness probe: confirms the app and DB are reachable."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok"}

# Create initial admin user if no users exist
def create_initial_admin():
    db = SessionLocal()
    try:
        user_count = db.query(func.count(User.id)).scalar()
        if user_count == 0:
            username = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
            password = os.getenv("INITIAL_ADMIN_PASSWORD")
            if not password:
                # Fail closed: never invent or log a credential. Operator must
                # provide one explicitly; until then no admin account exists.
                logger.error(
                    "No users exist and INITIAL_ADMIN_PASSWORD is not set. "
                    "Set INITIAL_ADMIN_PASSWORD (and optionally INITIAL_ADMIN_USERNAME) "
                    "and restart to create the initial admin account."
                )
                return
            admin_user = User(
                username=username,
                hashed_password=get_password_hash(password),
                role="admin",
                designation="System Administrator",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created initial admin '%s' from INITIAL_ADMIN_PASSWORD.", username)
    except Exception as e:
        logger.error(f"Error creating initial admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
