import warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, Depends, Request, Form, HTTPException, File, UploadFile, APIRouter
from fastapi import Query, Path
from typing import List  # Add this import
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Transport, Bus, Plane, Train, ProcessedMaster, User
import os
import csv
import io
from datetime import datetime
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ValidationError

def compress_its(its: int) -> str:
    try:
        its = str(its)
        print(len(its))
        if len(its) == 12:
            indices = [6, 5, 2, 7, 4, 0, 9, 8]
            compressed_its = ''.join(its[i] for i in indices)
            return int(compressed_its)
        elif len(its) == 8:
            return int(its)
        else:
            print("Error")
    except:
        return its


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Login route
@app.get("/")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login/")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password == password:
        response = RedirectResponse(url="/assign-sim-form/", status_code=303)
        response.set_cookie(key="username", value=username)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})

# Logout route
@app.get("/logout/")
async def logout(request: Request):
    response = RedirectResponse(url="/login/", status_code=303)
    response.delete_cookie("username")
    return response

# Get current user
def get_current_user(request: Request, db: Session = Depends(get_db)):
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.route("/assign-sim-form/", methods=["GET", "POST"])
async def get_assign_sim_form(request: Request, its: int = Form(...)):
    its = compress_its(its)
    if request.method == "POST":
        db = SessionLocal()
        master = db.query(Master).filter(Master.ITS == its).first()
        if not master:
            raise HTTPException(status_code=404, detail="Master not found")
        return templates.TemplateResponse("assign_sim_.html", {"request": request, "master": master})
    else:
        # Handle GET request here (if needed)
        return templates.TemplateResponse("assign_sim_.html", {"request": request})

@app.post("/assign-sim/", response_class=HTMLResponse)
async def assign_sim(request: Request, its: int = Form(...), db: Session = Depends(get_db)):
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    db.commit()
    db.refresh(master)
    return templates.TemplateResponse("assign_sim_.html", {"request": request, "master": master, "message": "SIM assigned successfully"})

@app.post("/update-phone/", response_class=HTMLResponse)
async def update_phone(request: Request, its: int = Form(...), phone_number: str = Form(...), db: Session = Depends(get_db)):
    its=compress_its(its)
    existing_master = db.query(Master).filter(Master.phone == phone_number).first()
    if existing_master and existing_master.ITS != its:
        error_message = "This phone number is already assigned to another ITS"
        master = db.query(Master).filter(Master.ITS == its).first()
        return templates.TemplateResponse("assign_sim_.html", {"request": request, "master": master, "error": error_message})
    
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    master.phone = phone_number
    db.commit()
    db.refresh(master)
    return templates.TemplateResponse("assign_sim_.html", {"request": request, "master": master, "message": "Phone number updated successfully"})

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
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
    