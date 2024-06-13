from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
import os

# Load environment variables
load_dotenv()

# Get the database URL from the environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for the models
Base = declarative_base()

# Import your SQLAlchemy models here
from database import Base, Master, Group, GroupInfo, BookingInfo, Transport, Bus, Train, Plane, Shuttle, Schedule, User, ProcessedMaster

# Create the FastAPI app
app = FastAPI()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency to get the SQLAlchemy session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.delete("/master")
def delete_all_master(db: Session = Depends(get_db)):
    db.query(Master).delete()
    db.commit()
    return JSONResponse(content={"message": "All records deleted successfully from Master table"})

@app.delete("/group")
def delete_all_group(db: Session = Depends(get_db)):
    db.query(Group).delete()
    db.commit()
    return JSONResponse(content={"message": "All records deleted successfully from Group table"})

@app.delete("/group_info")
def delete_all_group_info(db: Session = Depends(get_db)):
    db.query(GroupInfo).delete()
    db.commit()
    return JSONResponse(content={"message": "All records deleted successfully from GroupInfo table"})

@app.delete("/booking_info")
def delete_all_booking_info(db: Session = Depends(get_db)):
    db.query(BookingInfo).delete()
    db.commit()
    return JSONResponse(content={"message": "All records deleted successfully from BookingInfo table"})

@app.delete("/transport")
def delete_all_transport(db: Session = Depends(get_db)):
    db.query(Transport).delete()
    db.commit()
    return JSONResponse(content={"message": "All records deleted successfully from Transport table"})

@app.delete("/schedule")
def delete_all_schedule(db: Session = Depends(get_db)):
    db.query(Schedule).delete()
    db.commit()
    return JSONResponse(content={"message": "All records deleted successfully from Schedule table"})

@app.delete("/user")
def delete_all_user(db: Session = Depends(get_db)):
    db.query(User).delete()
    db.commit()
    return JSONResponse(content={"message": "All records deleted successfully from User table"})

@app.delete("/processed_master")
def delete_all_processed_master(db: Session = Depends(get_db)):
    db.query(ProcessedMaster).delete()
    db.commit()
    return JSONResponse(content={"message": "All records deleted successfully from ProcessedMaster table"})

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9696)
