from fastapi import FastAPI, Depends, Request, Form, HTTPException, File, UploadFile, APIRouter
from fastapi import Query, Path
from typing import List  # Add this import
from fastapi.responses import RedirectResponse,HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Transport, Bus, Plane, Train, ProcessedMaster, User, TrainDetails
import os
import csv
import io
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from datetime import datetime
from urllib.parse import unquote
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


# Main Index code with login check
@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# immigration Form

@app.get("/master-form")
def get_master_form(request: Request):
    return templates.TemplateResponse("master.html", {"request": request})
    
    

@app.get("/master/")
def get_master_by_its(request: Request, its: int, db: Session = Depends(get_db)):
    print("Master data updated")
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == int(its)).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    return templates.TemplateResponse("master.html", {"request": request, "master": master})

@app.post("/master/update", response_class=HTMLResponse)
async def update_master(
    request: Request,
    its: int = Form(...),
    first_name: str = Form(...),
    middle_name: str = Form(None),
    last_name: str = Form(...),
    passport_No: str = Form(...),
    passport_Expiry: str = Form(...),
    Visa_No: str = Form(None),
    db: Session = Depends(get_db)
):
    its = compress_its(its)
    
    # Check if the ITS is already processed
    if db.query(ProcessedMaster).filter(ProcessedMaster.ITS == int(its)).first():
        error_message = "This ITS entry has already been processed."
        master = db.query(Master).filter(Master.ITS == int(its)).first()
        return templates.TemplateResponse("master.html", {"request": request, "master": master, "error_message": error_message})
    
    master = db.query(Master).filter(Master.ITS == int(its)).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    # Move data to ProcessedMaster table
    processed_master = ProcessedMaster(
        ITS=master.ITS,
        first_name=master.first_name,
        middle_name=master.middle_name,
        last_name=master.last_name,
        DOB=master.DOB,
        passport_No=master.passport_No,
        passport_Expiry=master.passport_Expiry,
        Visa_No=master.Visa_No,
        Mode_of_Transport=master.Mode_of_Transport,
        phone=master.phone,
        arrived=master.arrived,
        timestamp=master.timestamp,
        processed_by="admin"  # Save the username of the current user
    )
    db.add(processed_master)
    
    # Update data in Master table
    master.first_name = first_name
    master.middle_name = middle_name
    master.last_name = last_name
    master.passport_No = passport_No
    master.passport_Expiry = datetime.strptime(passport_Expiry, "%Y-%m-%d").date()
    master.Visa_No = Visa_No
    
    db.commit()
    return templates.TemplateResponse("master.html", {"request": request, "master": master})




@app.get("/master/info/", response_class=HTMLResponse)
async def get_master_info(
    request: Request, 
    its: int = Query(..., description="ITS of the master to retrieve"), 
    db: Session = Depends(get_db)
):
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    return templates.TemplateResponse("master.html", {"request": request, "master": master})

# Add a new route to display data from the Master table in lists of 10
@app.get("/masters/", response_class=HTMLResponse)
async def list_masters(request: Request, page: int = Query(1), db: Session = Depends(get_db)):
    # Paginate the data
    page_size = 10
    offset = (page - 1) * page_size
    masters = db.query(Master).offset(offset).limit(page_size).all()

    # Get the total number of masters for pagination
    total_masters = db.query(func.count(Master.ITS)).scalar()

    return templates.TemplateResponse(
        "masters.html",
        {
            "request": request,
            "masters": masters,
            "page": page,
            "page_size": page_size,
            "total_masters": total_masters
        },
    )



# Mark as Arrived
@app.get("/mark-as-arrived/")
async def mark_as_arrived(its: int, db: Session = Depends(get_db)):
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    if master:
        master.arrived = True
        master.timestamp = datetime.now()
        db.commit()
        db.refresh(master)
        message = f"ITS {its} marked as arrived successfully"
    else:
        message = f"No record found for ITS {its}"
    return RedirectResponse(url=f"/mark-as-arrived-form/?its={its}&message={message}")

@app.get("/mark-as-arrived-form/")
async def get_mark_as_arrived_form(request: Request, its: int = None, message: str = None, db: Session = Depends(get_db)):
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    return templates.TemplateResponse("arrive.html", {"request": request, "master": master, "message": message})


# assign SIM

@app.route("/assign-sim-form", methods=["GET", "POST"])
async def get_assign_sim_form(request: Request, its: int = Form(...)):
    if request.method == "POST":
        db = SessionLocal()
        its = compress_its(its)
        master = db.query(Master).filter(Master.ITS == its).first()
        if not master:
            raise HTTPException(status_code=404, detail="Master not found")
        return templates.TemplateResponse("assign_sim.html", {"request": request, "master": master})
    else:
        # Handle GET request here (if needed)
        return templates.TemplateResponse("assign_sim.html", {"request": request})

@app.post("/assign-sim/", response_class=HTMLResponse)
async def assign_sim(request: Request, its: int = Form(...), db: Session = Depends(get_db)):
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    db.commit()
    db.refresh(master)
    return templates.TemplateResponse("assign_sim.html", {"request": request, "master": master, "message": "SIM assigned successfully"})

@app.post("/update-phone/", response_class=HTMLResponse)
async def update_phone(request: Request, its: int = Form(...), phone_number: str = Form(...), db: Session = Depends(get_db)):
    its = compress_its(its)
    existing_master = db.query(Master).filter(Master.phone == phone_number).first()
    if existing_master and existing_master.ITS != its:
        error_message = "This phone number is already assigned to another ITS"
        master = db.query(Master).filter(Master.ITS == its).first()
        return templates.TemplateResponse("assign_sim.html", {"request": request, "master": master, "error": error_message})
    
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    master.phone = phone_number
    db.commit()
    db.refresh(master)
    return templates.TemplateResponse("assign_sim.html", {"request": request, "master": master, "message": "Phone number updated successfully"})

# Bus Booking 

@app.get("/bus-booking/", response_class=HTMLResponse)
async def get_bus_booking_form(request: Request, its: int = Query(None), db: Session = Depends(get_db)):
    person = None
    buses = db.query(Bus).all()  # Fetch all buses
    search = its  # To display in the template if no person found
    
    if its:
        its = compress_its(its)
        person = db.query(Master).filter(Master.ITS == its).first()
    
    return templates.TemplateResponse("bus_booking.html", {"request": request, "person": person, "buses": buses, "search": search})

from sqlalchemy.exc import IntegrityError

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

        # Check if there are available seats
        if bus.no_of_seats <= 0:
            raise HTTPException(status_code=400, detail="No available seats for this bus")

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

        return templates.TemplateResponse(
            "bus_booking.html",
            {
                "request": request,
                "person": person,
                "buses": buses,
                "error": "No available seats for this bus"  # Pass the error message here
            },
        )

    except IntegrityError as e:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        buses = db.query(Bus).all()
        return templates.TemplateResponse(
            "bus_booking.html",
            {
                "request": request,
                "person": person,
                "buses": buses,
                "form_error": "An error occurred while booking: Seat already booked, please try again."
            },
        )

    except Exception as e:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        buses = db.query(Bus).all()
        return templates.TemplateResponse(
            "bus_booking.html",
            {
                "request": request,
                "person": person,
                "buses": buses,
                "form_error": "An error occurred while booking, please try again."
            },
        )

# View booking Info

# View booking Info
from fastapi import Query
from typing import Optional

@app.get("/view-booking-info/", response_class=HTMLResponse)
async def view_booking_info(request: Request, bus_number: Optional[int] = Query(None), db: Session = Depends(get_db)):
    # Filter by bus number if provided
    if bus_number:
        booking_info = db.query(BookingInfo, Master).join(Master).filter(BookingInfo.bus_number == bus_number).all()
    else:
        # If no bus number provided, fetch all booking info
        booking_info = db.query(BookingInfo, Master).join(Master).all()
    return templates.TemplateResponse("view_booking_info.html", {"request": request, "booking_info": booking_info})

# view busses

@app.get("/view-buses/")
def view_buses(request: Request, db: Session = Depends(get_db)):
    buses = db.query(Bus).all()
    return templates.TemplateResponse("view_buses.html", {"request": request, "buses": buses})

# view planes

@app.get("/view-planes/")
def view_planes(request: Request, db: Session = Depends(get_db)):
    planes = db.query(Plane).all()
    return templates.TemplateResponse("view_planes.html", {"request": request, "planes": planes})

# view trains

@app.get("/view-trains/")
def view_trains(request: Request, db: Session = Depends(get_db)):
    trains = db.query(Train).all()
    return templates.TemplateResponse("view_trains.html", {"request": request, "trains": trains})

# add buss

@app.get("/add-bus/")
def get_add_bus(request: Request):
    return templates.TemplateResponse("add_bus.html", {"request": request})


@app.post("/add-bus/")
def post_add_bus(request: Request, no_of_seats: int = Form(...), type: str = Form(...), db: Session = Depends(get_db)):
    # # Get the highest bus number from the database
    # try:
    #     highest_bus_number = int(db.query(func.max(Bus.bus_number)).scalar())
    # except:
    #     highest_bus_number = 0
    #     print("Exceptoion")
    last_bus = db.query(Bus).order_by(desc(Bus.id)).first()  # Assuming 'id' is the primary key
    next_bus_number = int(last_bus.bus_number) + 1 if last_bus else 1
    print(next_bus_number)
    
    new_bus = Bus(bus_number=next_bus_number, no_of_seats=no_of_seats, type=type)
    db.add(new_bus)
    db.commit()
    return RedirectResponse(url="/view-buses/", status_code=303)


# add plane

@app.get("/add-plane/")
def get_add_plane(request: Request):
    return templates.TemplateResponse("add_plane.html", {"request": request})

@app.post("/add-plane/")
def post_add_plane(request: Request, company: str = Form(...), type: str = Form(...), departure_time: str = Form(...), db: Session = Depends(get_db)):
    new_plane = Plane(company=company, type=type, departure_time=datetime.strptime(departure_time, '%Y-%m-%d').date())
    db.add(new_plane)
    db.commit()
    return RedirectResponse(url="/view-planes/", status_code=303)


# add train

@app.get("/add-train/")
def get_add_train(request: Request):
    return templates.TemplateResponse("add_train.html", {"request": request})

@app.post("/add-train/")
def post_add_train(request: Request, train_name: str = Form(...), departure_time: str = Form(...), db: Session = Depends(get_db)):
    parsed_time = datetime.strptime(departure_time, '%H:%M').time()
    new_train = Train(train_name=train_name, departure_time=parsed_time)
    db.add(new_train)
    db.commit()
    return RedirectResponse(url="/view-trains/", status_code=303)

# upload csv

@app.get("/upload-csv/")
def get_upload_csv(request: Request):
    return templates.TemplateResponse("upload_csv.html", {"request": request})

import uuid

@app.post("/upload-csv/")
async def post_upload_csv(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    csv_reader = csv.DictReader(io.StringIO(content.decode()))
    
    for row in csv_reader:
        full_name_parts = row["Full_Name"].split()
        first_name = full_name_parts[0]
        middle_name = full_name_parts[1] if len(full_name_parts) > 2 else ""
        last_name = full_name_parts[-1]
        
        # Parse date of birth
        dob_raw = row["Date of Birth"]
        try:
            dob = datetime.strptime(dob_raw, '%Y-%m-%d').date()
        except ValueError:
            dob = datetime.strptime(dob_raw, '%d/%m/%Y').date()  # Try another format
        
        # Parse passport expiry date
        expiry_date_raw = row["Passport Expiry Date"]
        try:
            expiry_date = datetime.strptime(expiry_date_raw, '%Y-%m-%d').date()
        except ValueError:
            expiry_date = datetime.strptime(expiry_date_raw, '%d/%m/%Y').date()  # Try another format
                
        new_master = Master(
            ITS=row["ITS_ID"],
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            DOB=dob,
            passport_No=row["Passoport Number"],
            passport_Expiry=expiry_date,
            Visa_No=row["Visa Number"],
            Mode_of_Transport="",
            phone = ""
        )
        db.add(new_master)
    
    db.commit()
    return RedirectResponse(url="/", status_code=303)



# APIs

@app.get("/{its}")
def get_master(its: int, db: Session = Depends(get_db)):
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        return JSONResponse(status_code=404, content={"error": "Master not found"})
    
    return JSONResponse(content={
        "ITS": master.ITS,
        "first_name": master.first_name,
        "middle_name": master.middle_name,
        "last_name": master.last_name,
        "passport_No": master.passport_No,
        "passport_Expiry": str(master.passport_Expiry),  # Convert to string for JSON serialization
        "Visa_No": master.Visa_No
    })

from fastapi import Depends

@app.get("/get_masters/")
def get_all_masters(db: Session = Depends(get_db)):
    masters = db.query(Master).all()
    if not masters:
        raise HTTPException(status_code=404, detail="No masters found")
    
    masters_data = [{"ITS": master.ITS} for master in masters]
    
    return {"masters": masters_data}

@app.get("/create-booking/", response_class=JSONResponse)
async def create_booking(
    request: Request,
    db: Session = Depends(get_db)
):
    print("Entered Function")
    # Decode URL-encoded query parameters
    query_string = str(request.url).split('?')[-1]
    print(query_string)
    params = query_string.split('&')
    print(params)

    its = int(params[0])
    seat_number = int(params[2])
    bus_number = int(params[1])

    # Check if ITS exists
    person = db.query(Master).filter(Master.ITS == its).first()
    if not person:
        raise HTTPException(status_code=404, detail="Master not found")

    # Check if bus exists
    bus = db.query(Bus).filter(Bus.bus_number == bus_number).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    # Check if the seat is available
    existing_booking = db.query(BookingInfo).filter(BookingInfo.bus_number == bus_number, BookingInfo.seat_number == seat_number).first()
    if existing_booking:
        raise HTTPException(status_code=400, detail="Seat already booked")

    # Create new booking
    new_booking = BookingInfo(
        ITS=its,
        Mode=1,  # assuming '1' represents 'bus' in your context
        Issued=True,
        Departed=False,
        Self_Issued=True,
        seat_number=seat_number,
        bus_number=bus_number
    )

    # Add the new booking to the session and commit
    db.add(new_booking)
    db.commit()

    # Decrement available seats
    bus.no_of_seats -= 1
    db.commit()

    return JSONResponse(content={"message": "Booking created successfully"})


router = APIRouter()
PAGE_SIZE = 10

# Get users
# def get_users(db: Session) -> List[User]:
#     return db.query(User).all()


@app.get("/processed-masters/", response_class=HTMLResponse)
async def get_processed_masters(
    request: Request,
    page: int = 1,
    user: str = None,  # Accept username from query parameter
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    total_count = db.query(func.count(ProcessedMaster.ITS)).scalar()

    # Base query for processed masters
    query = db.query(ProcessedMaster)

    # Apply username filter if username is provided
    if user:
        query = query.filter(ProcessedMaster.processed_by == user)

    # Retrieve processed masters for the current page
    processed_masters = (
        query.offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return templates.TemplateResponse(
        "processed_masters.html",
        {
            "request": request,
            "processed_masters": processed_masters,
            "page": page,
            "page_size": PAGE_SIZE,
            "total_count": total_count,
            "users": users,
            "selected_user": user,  # Pass the selected username to the template
        }
    )

@app.post("/print-processed-masters/", response_class=HTMLResponse)
async def print_processed_masters(page: int = Form(...), db: Session = Depends(get_db)):
    processed_masters = (
        db.query(ProcessedMaster)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    if not processed_masters:
        raise HTTPException(status_code=400, detail="No processed masters found for printing")

    # Render HTML for printing
    html_content = "<h2>Selected Processed Masters</h2><ul>"
    for master in processed_masters:
        html_content += f"<li>ITS: {master.ITS}, Name: {master.first_name} {master.last_name}</li>"
    html_content += "</ul>"

    return HTMLResponse(content=html_content)

@app.get("/booking-info/{bus_number}/")
def get_booking_info_for_bus(bus_number: int = Path(...), db: Session = Depends(get_db)):
    bookings = db.query(BookingInfo).filter(BookingInfo.bus_number == bus_number).all()
    if not bookings:
        raise HTTPException(status_code=404, detail="No booking information found for the specified bus ID")
    
    return JSONResponse(content=[{
        "booking_ITS": booking.ITS,
        "seat_number": booking.seat_number
    } for booking in bookings])
    
@app.get("/bus/")
def get_bus_info(db: Session = Depends(get_db)):
    bus = db.query(Bus).all()
    if not bus:
        raise HTTPException(status_code=404, detail="No Bus information found")
    return JSONResponse(content=[{
        "bus_number": busses.bus_number,
        "bus_type": busses.type
    } for busses in bus])
    

@app.get("/train-booking-form/", response_class=HTMLResponse)
async def get_train_booking_form(request: Request, its: int = Query(None), db: Session = Depends(get_db)):
    person = None
    trains = db.query(Train).all()  # Fetch all trains
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
        return templates.TemplateResponse("train_booking_form.html", {"request": request, "person": person, "trains": db.query(Train).all(), "message": "Train booked successfully"})
    except Exception as e:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        return templates.TemplateResponse("train_booking_form.html", {"request": request, "person": person, "trains": db.query(Train).all(), "error": f"Failed to book the train: {str(e)}"})


@app.get("/train-bookings/", response_class=HTMLResponse)
async def get_train_bookings(request: Request, db: Session = Depends(get_db)):
    trains = db.query(Train).all()
    train_data = [{
        "id": train.id,
        "train_name": train.train_name,
        "departure_time": train.departure_time.isoformat()
    } for train in trains]
    return templates.TemplateResponse("train_bookings.html", {"request": request, "trains": train_data})

# Define a function to fetch aggregated train bookings with ITS details
def get_train_bookings_with_details(db: Session) -> List[dict]:
    train_bookings = db.query(TrainDetails).all()
    result = []
    for booking in train_bookings:
        master_details = db.query(Master).filter(Master.ITS == booking.ITS).first()
        if master_details:
            result.append({
                "train_name": booking.train_number,
                "ITS": master_details.ITS,
                "first_name": master_details.first_name,
                "middle_name": master_details.middle_name,
                "last_name": master_details.last_name,
                "phone": master_details.phone,
                "passport_No": master_details.passport_No,
                "Visa_No": master_details.Visa_No
            })
    return result

@app.get("/api/check_processed_its", response_model=bool)
async def check_processed_its(its: int, db: Session = Depends(get_db)):
    its = compress_its(its)
    exists = db.query(ProcessedMaster).filter(ProcessedMaster.ITS == int(its)).first() is not None
    return exists

async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

# Middleware to catch all other 404 errors
@app.middleware("http")
async def custom_404_handler(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return response

# Fallback route for undefined paths
@app.get("/{full_path:path}")
async def fallback_404(request: Request):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
