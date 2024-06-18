from fastapi import FastAPI, Depends, Request, Form, HTTPException, File, UploadFile, APIRouter
from fastapi import Query, Path
from typing import List  # Add this import
from fastapi.responses import RedirectResponse,HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Transport, Bus, Plane, Train, GroupInfo, Group, ProcessedMaster, User, TrainDetails
import os
import csv
import io
from datetime import datetime
from fastapi.responses import JSONResponse
from datetime import datetime
from urllib.parse import unquote

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


@app.get("/", response_class=HTMLResponse)
async def get_train_booking_form(request: Request, its: int = Query(None), db: Session = Depends(get_db)):
    person = None
    trains = db.query(Train).all()  # Fetch all buses
    search = its  # To display in the template if no person found

    if its:
        person = db.query(Master).filter(Master.ITS == its).first()
    
    return templates.TemplateResponse("train_booking_form.html", {"request": request, "person": person, "trains": trains, "search": search})

@app.post("/book-train-details/", response_class=HTMLResponse)
async def book_train_details(
    request: Request,
    its: int = Form(...),
    train_number: str = Form(...),
    seat_number: int = Form(...),
    coach_number: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        train = db.query(Train).filter(Train.train_number == train_number).first()
        if not train:
            raise HTTPException(status_code=404, detail="Train not found")

        new_train_details = TrainDetails(
            train_number=train_number,
            seat_number=seat_number,
            coach_number=coach_number
        )
        db.add(new_train_details)
        db.commit()
        db.refresh(new_train_details)

        new_booking = BookingInfo(
            ITS=its,
            Mode=3,
            Issued=True,
            Departed=False,
            Self_Issued=True,
            train_details_id=new_train_details.id
        )
        db.add(new_booking)
        db.commit()

        person = db.query(Master).filter(Master.ITS == its).first()
        return templates.TemplateResponse("train_booking_form.html", {"request": request, "person": person, "message": "Train booked successfully"})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to book the train: {str(e)}")
    
@app.get("/train-bookings/", response_class=HTMLResponse)
async def get_train_bookings(request: Request, db: Session = Depends(get_db)):
    train_bookings = get_train_bookings_with_details(db)
    return templates.TemplateResponse("train_bookings.html", {"request": request, "bookings": train_bookings})

# Define a function to fetch aggregated train bookings with ITS details
def get_train_bookings_with_details(db: Session) -> List[dict]:
    train_bookings = db.query(TrainDetails).all()
    result = []
    for booking in train_bookings:
        master_details = db.query(Master).filter(Master.ITS == booking.ITS).first()
        if master_details:
            result.append({
                "train_name": booking.train_name,
                "ITS": booking.ITS,
                "first_name": master_details.first_name,
                "middle_name": master_details.middle_name,
                "last_name": master_details.last_name,
                "phone": master_details.phone,
                "passport_No": master_details.passport_No,
                "Visa_No": master_details.Visa_No
            })
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 2500)))
