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
from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Bus, Plane, ProcessedMaster, User
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
        response = RedirectResponse(url="/plane-booking-form/", status_code=303)
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


@app.get("/plane-booking-form/", response_class=HTMLResponse)
async def post_plane_booking_form(request: Request, its: int = None, db: Session = Depends(get_db)):
    print(its)
    person = None
    
    if its:
        its = compress_its(its)
        person = db.query(Master).filter(Master.ITS == its).first()
    planes = db.query(Plane).all()
    search = its if its else ""

    return templates.TemplateResponse("plane_booking_form_.html", {
        "request": request,
        "person": person,
        "planes": planes,
        "search": search
    })
    
    
@app.get("/book-plane-details/", response_class=HTMLResponse)
async def post_book_plane(
    request: Request,
    its: int,
    plane_name: str,
    seat_number: int ,
    db: Session = Depends(get_db)
):
    print("entered form")
    try:
        # Check if ITS exists and fetch its details
        person = db.query(Master).filter(Master.ITS == its).first()
        if not person:
            raise HTTPException(status_code=404, detail=f"ITS {its} not found")

        # Check if plane exists and fetch its details
        plane = db.query(Plane).filter(Plane.plane_id == plane_name).first()
        if not plane:
            raise HTTPException(status_code=404, detail=f"Plane {plane_name} not found")

        # Book the plane seat
        new_booking = BookingInfo(
            ITS=its,
            Mode=3,  # Assuming '2' represents 'plane' in your context
            Issued=True,
            Departed=False,
            Self_Issued=True,
            seat_number=seat_number,
            plane_id=plane_name
        )
        shuttle_id = 'P' + str(new_booking.plane_id)
        date_time = datetime.combine(datetime.today(), db.query(Plane).filter(Plane.plane_id == new_booking.plane_id).first().departure_time)
        plane = db.query(Plane).filter(Plane.plane_id == new_booking.plane_id).first()
        # Subtract two hours
        shuttle_time = (date_time - timedelta(hours=2)).time()
        db.add(new_booking)
        db.commit()

        # Retrieve person and planes for template
        planes = db.query(Plane).all()

        return templates.TemplateResponse(
            "plane_booking_form_.html",
            {
                "request": request,
                "person": person,
                "planes": planes,
                "plane":plane,
                "booking": new_booking,
                "shuttle_id": shuttle_id,
                "departure_time": shuttle_time, 
                "message": "Plane booked successfully"
            },
        )


    except IntegrityError:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        planes = db.query(Plane).all()
        return templates.TemplateResponse(
            "plane_booking_form_.html",
            {
                "request": request,
                "person": person,
                "planes": planes,
                "form_error": "An error occurred while booking: Seat already booked, please try again."
            },
        )

    except HTTPException as e:
        person = db.query(Master).filter(Master.ITS == its).first()
        planes = db.query(Plane).all()
        return templates.TemplateResponse(
            "plane_booking_form_.html",
            {
                "request": request,
                "person": person,
                "planes": planes,
                "form_error": f"An error occurred while booking: {e.detail}"
            },
        )

    except Exception as e:
        print(e)
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        planes = db.query(Plane).all()
        return templates.TemplateResponse(
            "plane_booking_form_.html",
            {
                "request": request,
                "person": person,
                "planes": planes,
                "form_error": "An unexpected error occurred while booking, please try again."
            },
        )   

from sqlalchemy import func

@app.get("/plane_info/", response_class=HTMLResponse)
async def view_plane_booking(request: Request, db: Session = Depends(get_db)):
    # Query to get BookingInfo
    booking_query = db.query(
        BookingInfo.plane_id,
        BookingInfo.ITS,
        BookingInfo.seat_number
    ).filter(BookingInfo.Mode == 3).subquery()
    
    # Query to get Master details
    master_query = db.query(
        Master.ITS.label('master_ITS'),
        Master.first_name,
        Master.passport_No,
        Master.phone
    ).subquery()
    
    # Query to get plane details
    plane_query = db.query(
        Plane.plane_id.label('plane_id'),
        Plane.company,
        Plane.departure_time
    ).subquery()
    
    # Perform union of the queries and calculate the shuttle time
    result = db.query(
        booking_query.c.plane_id,
        master_query.c.first_name,
        master_query.c.passport_No,
        master_query.c.phone,
        booking_query.c.ITS,
        booking_query.c.seat_number,
        plane_query.c.company,
        plane_query.c.departure_time,
        func.strftime('%H:%M:%S', func.datetime(plane_query.c.departure_time, '-4 hours')).label('shuttle_time')
    ).join(
        master_query, master_query.c.master_ITS == booking_query.c.ITS
    ).join(
        plane_query, plane_query.c.plane_id == booking_query.c.plane_id
    ).all()
    
    booking_details = [
        {
            "plane_id": row.plane_id,
            "plane_name": row.company,
            "departure_time": row.departure_time,
            "shuttle_time": row.shuttle_time,
            "ITS": row.ITS,
            "passenger_name": row.first_name,
            "passport_number": row.passport_No,
            "phone_number": row.phone,
            "seat_number": row.seat_number
        }
        for row in result
    ]
    
    if not booking_details:
        print("No bookings")
    
    return templates.TemplateResponse('plane_bookings_.html', {"request": request, "bookings": booking_details})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 6001)))
