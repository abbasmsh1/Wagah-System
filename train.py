from fastapi import FastAPI, Depends, Request, Form, HTTPException, File, UploadFile, APIRouter
from fastapi import Query, Path
from typing import List  # Add this import
from fastapi.responses import RedirectResponse,HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Transport, Bus, Plane, Train, ProcessedMaster, User
import os
import csv
import io
from datetime import datetime
from fastapi.responses import JSONResponse
from datetime import datetime
from urllib.parse import unquote
from sqlalchemy.exc import IntegrityError

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

# Dependency to get the DB session
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
        response = RedirectResponse(url="/train-booking-form/", status_code=303)
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

@app.get("/train-booking-form/", response_class=HTMLResponse)
async def post_train_booking_form(request: Request, its: int = None, db: Session = Depends(get_db)):
    person = None
    if its:
        its = compress_its(its)
        print(its)
        person = db.query(Master).filter(Master.ITS == its).first()
    trains = db.query(Train).all()
    search = its if its else ""

    return templates.TemplateResponse("train_booking_form_.html", {
        "request": request,
        "person": person,
        "trains": trains,
        "search": search
    })
    
    
@app.get("/book-train-details/", response_class=HTMLResponse)
async def post_book_train(
    request: Request,
    its: int,
    train_number: int,
    seat_number: str ,
    coach_number: str,
    cabin_number: str,
    db: Session = Depends(get_db)
):
    its=compress_its(its)
    try:
        # Check if ITS exists and fetch its details
        person = db.query(Master).filter(Master.ITS == its).first()
        if not person:
            raise HTTPException(status_code=404, detail=f"ITS {its} not found")

        # Check if train exists and fetch its details
        train = db.query(Train).filter(Train.id == train_number).first()
        if not train:
            raise HTTPException(status_code=404, detail=f"Train {train_number} not found")

        # Book the train seat
        new_booking = BookingInfo(
            ITS=its,
            Mode=2,  # Assuming '2' represents 'train' in your context
            Issued=True,
            Departed=False,
            Self_Issued=True,
            seat_number=seat_number,
            train_id=train_number,
            coach_number=coach_number,
            cabin_number = cabin_number
        )
        db.add(new_booking)
        db.commit()

        # Retrieve person and trains for template
        trains = db.query(Train).all()

        return templates.TemplateResponse(
            "train_booking_form_.html",
            {
                "request": request,
                "person": person,
                "trains": trains,
                "message": "Train booked successfully"
            },
        )

    except IntegrityError:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        trains = db.query(Train).all()
        return templates.TemplateResponse(
            "train_booking_form_.html",
            {
                "request": request,
                "person": person,
                "trains": trains,
                "form_error": "An error occurred while booking: Seat already booked, please try again."
            },
        )

    except HTTPException as e:
        person = db.query(Master).filter(Master.ITS == its).first()
        trains = db.query(Train).all()
        return templates.TemplateResponse(
            "train_booking_form_.html",
            {
                "request": request,
                "person": person,
                "trains": trains,
                "form_error": f"An error occurred while booking: {e.detail}"
            },
        )

    except Exception:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        trains = db.query(Train).all()
        return templates.TemplateResponse(
            "train_booking_form_.html",
            {
                "request": request,
                "person": person,
                "trains": trains,
                "form_error": "An unexpected error occurred while booking, please try again."
            },
        )   

from sqlalchemy import func

@app.get("/train_info/", response_class=HTMLResponse)
async def view_train_booking(request: Request, db: Session = Depends(get_db)):
    # Query to get BookingInfo
    booking_query = db.query(
        BookingInfo.train_id,
        BookingInfo.ITS,
        BookingInfo.seat_number,
        BookingInfo.coach_number,
        BookingInfo.cabin_number
    ).filter(BookingInfo.Mode == 2).subquery()
    
    # Query to get Master details
    master_query = db.query(
        Master.ITS.label('master_ITS'),
        Master.first_name,
        Master.passport_No,
        Master.phone
    ).subquery()
    
    # Query to get Train details
    train_query = db.query(
        Train.id.label('train_id'),
        Train.train_name,
        Train.departure_time
    ).subquery()
    
    # Perform union of the queries and calculate the shuttle time
    result = db.query(
        booking_query.c.train_id,
        master_query.c.first_name,
        master_query.c.passport_No,
        master_query.c.phone,
        booking_query.c.ITS,
        booking_query.c.seat_number,
        booking_query.c.coach_number,
        booking_query.c.cabin_number,
        train_query.c.train_name,
        train_query.c.departure_time,
        func.strftime('%H:%M:%S', func.datetime(train_query.c.departure_time, '-2 hours')).label('shuttle_time')
    ).join(
        master_query, master_query.c.master_ITS == booking_query.c.ITS
    ).join(
        train_query, train_query.c.train_id == booking_query.c.train_id
    ).all()
    
    booking_details = [
        {
            "train_id": row.train_id,
            "train_name": row.train_name,
            "departure_time": row.departure_time,
            "shuttle_time": row.shuttle_time,
            "ITS": row.ITS,
            "passenger_name": row.first_name,
            "passport_number": row.passport_No,
            "phone_number": row.phone,
            "seat_number": row.seat_number,
            "coach_number": row.coach_number,
            "cabin_number": row.cabin_number
        }
        for row in result
    ]
    
    if not booking_details:
        print("No bookings")
    
    return templates.TemplateResponse('train_bookings_.html', {"request": request, "bookings": booking_details})

@app.get("/count-train/")
def view_train_count(request: Request, db: Session = Depends(get_db)):
    try:
        booking_counts = db.query(BookingInfo.train_id,func.count(BookingInfo.train_id).label("passenger_count")).group_by(BookingInfo.train_id).all()
        # Render the template and pass the data
        return templates.TemplateResponse("train_counts.html", {"request": request,"booking_counts": booking_counts})
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
