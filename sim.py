from fastapi import FastAPI, Depends, Request, Form, HTTPException, File, UploadFile, APIRouter
from fastapi import Query, Path
from typing import List  # Add this import
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Transport, Bus, Plane, Train, GroupInfo, Group, ProcessedMaster, User
import os
import csv
import io
from datetime import datetime

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
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    db.commit()
    db.refresh(master)
    return templates.TemplateResponse("assign_sim_.html", {"request": request, "master": master, "message": "SIM assigned successfully"})

@app.post("/update-phone/", response_class=HTMLResponse)
async def update_phone(request: Request, its: int = Form(...), phone_number: str = Form(...), db: Session = Depends(get_db)):
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
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 2000)))
    