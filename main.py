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
    arrived_count = db.query(Master).filter(Master.arrived == True).count()
    return templates.TemplateResponse("arrive.html", {"request": request, "master": master, "message": message, "arrived_count": arrived_count})


@app.get("/arrived-list/", response_class=HTMLResponse)
async def arrived_list(request: Request, db: Session = Depends(get_db)):
    arrived_masters = db.query(Master).filter(Master.arrived == True).order_by(desc(Master.timestamp)).all()
    return templates.TemplateResponse("arrived_list.html", {"request": request, "arrived_masters": arrived_masters})


# assign SIM

@app.route("/assign-sim-form/", methods=["GET", "POST"])
async def get_assign_sim_form(request: Request, its: int = Form(...)):
    its = compress_its(its)
    if request.method == "POST":
        db = SessionLocal()
        master = db.query(Master).filter(Master.ITS == its).first()
        sim_count = db.query(func.count(Master.ITS)).filter(Master.phone.is_not(None), Master.phone != '').scalar()
        if not master:
            raise HTTPException(status_code=404, detail="Master not found")
        return templates.TemplateResponse("assign_sim.html", {"request": request, "master": master, "sim_count": sim_count})
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
    its=compress_its(its)
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

@app.get("/phone-list/", response_class=HTMLResponse)
async def get_phone_list(request: Request, db: Session = Depends(get_db)):
    phone_assigned = db.query(Master).filter(Master.phone.isnot(None), Master.phone != '').order_by(desc(Master.timestamp)).all()
    return templates.TemplateResponse("sim_list.html", {"request": request, "phone_assigned": phone_assigned})

# Bus Booking 


from sqlalchemy.exc import IntegrityError
from fastapi import Query
from typing import Optional

# View booking Info
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
    
    return templates.TemplateResponse("bus_booking.html", {"request": request, "person": person, "buses": buses, "search": search})

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
            "bus_booking.html",
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
            "bus_booking.html",
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
            "bus_booking.html",
            {
                "request": request,
                "person": person,
                "buses": buses,
                "booked_ticket":info,
                "form_error": "An error occurred while booking, please try again."
            },
        )    

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

# view report count

@app.get("/view-count/")
def view_all_count(request: Request, db: Session = Depends(get_db)):
    try:
        # Count of processed masters
        processed_count = db.query(func.count(ProcessedMaster.id)).scalar()
        
        # count of masters who have done arrival scanning
        arrived_count = db.query(func.count(Master.ITS)).filter(Master.arrived == True).scalar()

        # count of masters who has been assinged a sim
        sim_count = db.query(func.count(Master.ITS)).filter(Master.phone.is_not(None), Master.phone != '').scalar()

        # Count of unique masters who booked a bus seat
        bus_booking_count = db.query(func.count(func.distinct(Master.ITS))).\
            join(BookingInfo, Master.ITS == BookingInfo.ITS).\
            filter(BookingInfo.Mode == 1).\
            scalar()
        
        # count of unique masters who booked a train seat
        train_booking_count = db.query(func.count(func.distinct(Master.ITS))).\
            join(BookingInfo, Master.ITS == BookingInfo.ITS).\
            filter(BookingInfo.train_id.isnot(None)).\
            scalar()
        
        # count of unique masters who booked a plane seat
        plane_booking_count = db.query(func.count(Master.ITS)).\
            join(BookingInfo, Master.ITS == BookingInfo.ITS).\
            filter(BookingInfo.plane_id.isnot(None)).\
            scalar()

        # Render the template and pass the data
        return templates.TemplateResponse("view_count.html", {
            "request": request,
            "processed_count": processed_count,
            "bus_booking_count": bus_booking_count,
            "arrived_count": arrived_count,
            "sim_count": sim_count,
            "train_booking_count": train_booking_count,
            "plane_booking_count": plane_booking_count
        })
    except Exception as e:
        return {"error": str(e)}


@app.get("/count-train/")
def view_train_count(request: Request, db: Session = Depends(get_db)):
    try:
        booking_counts = (
    db.query(
        Train.train_name,
        Train.departure_time,
        BookingInfo.train_id,
        func.count(BookingInfo.train_id).label("passenger_count"),
    )
    .join(Train, Train.id == BookingInfo.train_id)
    .group_by(Train.train_name, Train.departure_time, BookingInfo.train_id)
    .all()
)
        # Render the template and pass the data
        return templates.TemplateResponse("train_counts.html", {"request": request,"booking_counts": booking_counts})
    except Exception as e:
        return {"error": str(e)}

@app.get("/count-bus/")
def view_bus_count(request: Request, db: Session = Depends(get_db)):
    try:
        booking_counts = db.query(BookingInfo.bus_number,func.count(BookingInfo.bus_number).label("passenger_count")).group_by(BookingInfo.bus_number).all()
        # Render the template and pass the data
        return templates.TemplateResponse("bus_counts.html", {"request": request,"booking_counts": booking_counts})
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/count-plane/")
def view_bus_count(request: Request, db: Session = Depends(get_db)):
    try:
        booking_counts = (
            db.query(BookingInfo.plane_id,
                                  Plane.company,Plane.departure_time,
                                  func.count(BookingInfo.plane_id).label("passenger_count"),
                                  ).join(Plane, Plane.plane_id == BookingInfo.plane_id)
            .group_by(Plane.company, Plane.departure_time, BookingInfo.plane_id)
            .all())
        # Render the template and pass the data
        return templates.TemplateResponse("plane_counts.html", {"request": request,"booking_counts": booking_counts})
    except Exception as e:
        return {"error": str(e)}

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


# Define the routes
@app.get("/add-plane/", response_class=HTMLResponse)
async def get_add_plane(request: Request):
    return templates.TemplateResponse("add_plane.html", {"request": request})

@app.post("/add-plane/")
async def post_add_plane(
    request: Request,
    company: str = Form(...),
    departure_time: str = Form(...),  # Expecting the time in HH:MM format
    db: Session = Depends(get_db)
):
    # Parse the departure time string to a time object
    parsed_time = datetime.strptime(departure_time, '%H:%M').time()
    new_plane = Plane(company=company, departure_time=parsed_time)
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
async def post_train_booking_form(request: Request, its: int = None, db: Session = Depends(get_db)):
    person = None
    if its:
        its = compress_its(its)
        print(its)
        person = db.query(Master).filter(Master.ITS == its).first()
    trains = db.query(Train).all()
    search = its if its else ""

    return templates.TemplateResponse("train_booking_form.html", {
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
        shuttle_id = 'T' + str(new_booking.train_id)
        # Convert datetime.time to datetime.datetime (using an arbitrary date)
        date_time = datetime.combine(datetime.today(), db.query(Train).filter(Train.id == new_booking.train_id).first().departure_time)
        train = db.query(Train).filter(Train.id == new_booking.train_id).first()
        # Subtract two hours
        shuttle_time = (date_time - timedelta(hours=2)).time()
        db.add(new_booking)
        db.commit()

        # Retrieve person and trains for template
        trains = db.query(Train).all()

        return templates.TemplateResponse(
            "train_booking_form.html",
            {
                "request": request,
                "person": person,
                "trains": trains,
                "train":train,
                "booking": new_booking,
                "shuttle_id": shuttle_id,
                "departure_time": shuttle_time, 
                "message": "Train booked successfully"
            },
        )

    except IntegrityError:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        trains = db.query(Train).all()
        return templates.TemplateResponse(
            "train_booking_form.html",
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
            "train_booking_form.html",
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
    
    return templates.TemplateResponse('train_bookings.html', {"request": request, "bookings": booking_details})

@app.get("/api/check_processed_its", response_model=bool)
async def check_processed_its(its: int, db: Session = Depends(get_db)):
    its = compress_its(its)
    exists = db.query(ProcessedMaster).filter(ProcessedMaster.ITS == int(its)).first() is not None
    return exists

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


@app.get("/plane-booking-form/", response_class=HTMLResponse)
async def post_plane_booking_form(request: Request, its: int = None, db: Session = Depends(get_db)):
    print(its)
    person=None
    if its:
        its = compress_its(its)
        print(its)
        person = db.query(Master).filter(Master.ITS == its).first()
        print(person.ITS)
    planes = db.query(Plane).all()
    search = its if its else ""

    return templates.TemplateResponse("plane_booking_form.html", {
        "request": request,
        "person": person,
        "planes": planes,
        "search": search
    })
    
    
@app.get("/book-plane-details/", response_class=HTMLResponse)
async def post_book_train(
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

        # Check if train exists and fetch its details
        plane = db.query(Plane).filter(Plane.plane_id == plane_name).first()
        if not plane:
            raise HTTPException(status_code=404, detail=f"Plane {plane_name} not found")

        # Book the train seat
        new_booking = BookingInfo(
            ITS=its,
            Mode=3,  # Assuming '2' represents 'train' in your context
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

        # Retrieve person and trains for template
        planes = db.query(Plane).all()

        return templates.TemplateResponse(
            "plane_booking_form.html",
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
            "plane_booking_form.html",
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
            "plane_booking_form.html",
            {
                "request": request,
                "person": person,
                "planes": planes,
                "form_error": f"An error occurred while booking: {e.detail}"
            },
        )

    except Exception:
        db.rollback()
        person = db.query(Master).filter(Master.ITS == its).first()
        planes = db.query(Plane).all()
        return templates.TemplateResponse(
            "plane_booking_form.html",
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
    
    # Query to get Train details
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
    
    return templates.TemplateResponse('plane_bookings.html', {"request": request, "bookings": booking_details})


# Mark as Departed
@app.get("/mark-as-departed/")
async def mark_as_departed(its: int, db: Session = Depends(get_db)):
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    if master:
        master.departed = True
        master.d_timestamp = datetime.now()
        db.commit()
        db.refresh(master)
        message = f"ITS {its} marked as Departed successfully"
    else:
        message = f"No record found for ITS {its}"
    return RedirectResponse(url=f"/mark-as-departed-form/?its={its}&message={message}")

@app.get("/mark-as-departed-form/")
async def get_mark_as_departed_form(request: Request, its: int = None, message: str = None, db: Session = Depends(get_db)):
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    departed_count = db.query(Master).filter(Master.departed == True).count()
    return templates.TemplateResponse("departed.html", {"request": request, "master": master, "message": message, "departed_count": departed_count})

@app.get("/departed-list/", response_class=HTMLResponse)
async def departed_list(request: Request, page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    page_size = 16
    departed_masters = db.query(Master).filter(Master.departed == True).order_by(Master.d_timestamp).offset((page-1)*page_size).limit(page_size).all()
    total_count = db.query(Master).filter(Master.departed == True).count()
    return templates.TemplateResponse("departed_list.html", {
        "request": request,
        "masters": departed_masters,
        "total_count": total_count,
        "page_size": page_size,
        "current_page": page
    })

@app.get("/its-form/", response_class=HTMLResponse)
async def get_its_form(request: Request):
    return templates.TemplateResponse("its_form.html", {"request": request})

@app.post("/print-its-form", response_class=HTMLResponse)
async def print_its_form(request: Request, its_numbers: str = Form(...), db: Session = Depends(get_db)):
    its_list = [int(its.strip()) for its in its_numbers.split(",")]
    results = (
        db.query(Master, BookingInfo)
        .join(BookingInfo, Master.ITS == BookingInfo.ITS)
        .filter(Master.ITS.in_(its_list))
        .all()
    )
    bookings = [
        {
            "ITS": master.ITS,
            "first_name": master.first_name,
            "middle_name": master.middle_name,
            "last_name": master.last_name,
            "bus_number": booking.bus_number,
            "seat_number": booking.seat_number,
        }
        for master, booking in results
    ]
    return templates.TemplateResponse("printable_form.html", {"request": request, "bookings": bookings})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
