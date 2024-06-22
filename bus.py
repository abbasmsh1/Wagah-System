import warnings

warnings.filterwarnings("ignore")
from fastapi import FastAPI, Depends, Request, Form, HTTPException, File, UploadFile, APIRouter
from fastapi import Query, Path
from typing import List  # Add this import
from fastapi.responses import RedirectResponse,HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Bus, Plane, Train, ProcessedMaster, User
import os
import csv
import io
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from datetime import datetime
from urllib.parse import unquote
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ValidationError
from sqlalchemy.orm import Session, joinedload
from datetime import timedelta
from datetime import time
from sqlalchemy.exc import IntegrityError
from fastapi import Query
from typing import Optional

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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

group_numbers = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login/")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password == password:
        response = RedirectResponse(url="/bus-booking/", status_code=303)
        response.set_cookie(key="username", value=username)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})

@app.get("/logout/")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("username")
    return response

def get_current_user(request: Request, db: Session = Depends(get_db)):
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/view-booking-info/", response_class=HTMLResponse)
async def view_booking_info(request: Request, bus_number: Optional[int] = Query(None), db: Session = Depends(get_db)):
    # Filter by bus number if provided
    if bus_number:
        booking_info = db.query(BookingInfo, Master).join(Master).filter(BookingInfo.bus_number == bus_number).all()
    else:
        # If no bus number provided, fetch all booking info
        booking_info = db.query(BookingInfo, Master).join(Master).all()
    return templates.TemplateResponse("view_booking_info.html", {"request": request, "booking_info": booking_info})

@app.get("/bus-booking/", response_class=HTMLResponse)
async def get_bus_booking_form(request: Request, its: int = Query(None), db: Session = Depends(get_db)):
    person = None
    its = compress_its(its)
    buses = db.query(Bus).all()  # Fetch all buses
    search = its  # To display in the template if no person found
    
    if its:
        its = compress_its(its)
        person = db.query(Master).filter(Master.ITS == its).first()
    
    return templates.TemplateResponse("bus_booking_.html", {"request": request, "person": person, "buses": buses, "search": search})

@app.post("/book-bus/", response_class=HTMLResponse)
async def post_book_bus(
    request: Request,
    its: int = Form(...),
    bus_number: str = Form(...),
    db: Session = Depends(get_db)
):
    its = compress_its(its)
    try:
        # Check if bus exists and fetch its details
        bus = db.query(Bus).filter(Bus.bus_number == bus_number).first()
        if not bus:
            raise HTTPException(status_code=404, detail=f"Bus {bus_number} not found")

        # Fetch the next available seat number
        booked_seats = db.query(BookingInfo.seat_number).filter(
            BookingInfo.bus_number == bus_number
        ).all()
        booked_seats = [seat[0] for seat in booked_seats if seat[0] is not None]
        next_seat_number = 1
        while next_seat_number in booked_seats:
            next_seat_number += 1

        # Book the seat
        new_booking = BookingInfo(
            ITS=its,
            Mode=1,  # assuming '1' represents 'bus' in your context
            Issued=True,
            Departed=False,
            Self_Issued=True,
            seat_number=next_seat_number,
            bus_number=bus_number
        )
        db.add(new_booking)
        db.commit()

        # Decrement available seats
        bus.no_of_seats -= 1
        db.commit()

        # Retrieve person and buses for template
        person = db.query(Master).filter(Master.ITS == its).first()
        buses = db.query(Bus).all()
        info = db.query(BookingInfo).filter(BookingInfo.ITS == its).first()
        print(info)
        return templates.TemplateResponse(
            "bus_booking_.html",
            {
                "request": request,
                "person": person,
                "buses": buses,
                "booked_ticket":info,
                "success": "Seat Booked"  # Pass the error message here
            },
        )

    except IntegrityError as e:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        buses = db.query(Bus).all()
        info = db.query(BookingInfo).filter(BookingInfo.ITS == its).first()
        return templates.TemplateResponse(
            "bus_booking_.html",
            {
                "request": request,
                "person": person,
                "buses": buses,
                "booked_ticket":info,
                "form_error": "An error occurred while booking: Seat already booked, please try again."
            },
        )

    except Exception as e:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        buses = db.query(Bus).all()
        info = db.query(BookingInfo).filter(BookingInfo.ITS == its).first()
        return templates.TemplateResponse(
            "bus_booking_.html",
            {
                "request": request,
                "person": person,
                "buses": buses,
                "booked_ticket":info,
                "form_error": "An error occurred while booking, please try again."
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 4000)))
