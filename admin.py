import warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, Form, Request, APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from database import SessionLocal, User
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ValidationError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from middleware.auth import admin_required
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to hash password
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Function to retrieve all users from the database
def get_users(db: Session):
    try:
        users = db.query(User).all()
        return users
    except Exception as e:
        print(f"Error getting users: {e}")
        return []

# Function to add a new user to the database
def add_user(db: Session, username: str, password: str, designation: str, role: str = "user"):
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return False, "Username already exists"

        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create new user
        new_user = User(
            username=username,
            hashed_password=hashed_password,
            role=role,
            designation=designation,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return True, "User added successfully"
    except Exception as e:
        db.rollback()
        return False, f"Failed to add user: {str(e)}"

@router.get("/users/add", response_class=HTMLResponse)
async def render_add_user_form(
    request: Request,
    message: str = None,
    _: bool = Depends(admin_required)
):
    return templates.TemplateResponse(
        "admin/add_user.html",
        {
            "request": request,
            "message": message
        }
    )

# Route to handle the form submission and add the new user to the database
@router.post("/users/add")
async def add_new_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    designation: str = Form(...),
    db: Session = Depends(get_db),
    _: bool = Depends(admin_required)
):
    success, message = add_user(db, username, password, designation)
    if success:
        return RedirectResponse(url="/admin/users", status_code=303)
    else:
        return templates.TemplateResponse(
            "admin/add_user.html",
            {
                "request": request,
                "message": message
            },
            status_code=400
        )

# Route to display all users
@router.get("/users", response_class=HTMLResponse)
async def display_users(
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(admin_required)
):
    users = get_users(db)
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": users
        }
    )

# async def http_exception_handler(request: Request, exc: HTTPException):
#     if exc.status_code == 404:
#         return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
#     return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

# @app.exception_handler(Exception)
# async def general_exception_handler(request: Request, exc: Exception):
#     return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

# # Middleware to catch all other 404 errors
# @app.middleware("http")
# async def custom_404_handler(request: Request, call_next):
#     response = await call_next(request)
#     if response.status_code == 404:
#         return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
#     return response

# # Fallback route for undefined paths
# @app.get("/{full_path:path}")
# async def fallback_404(request: Request):
#     return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9630)