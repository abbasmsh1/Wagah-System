from fastapi import FastAPI, Depends, Request, Form, HTTPException, File, UploadFile, APIRouter, Request,  Query, Path
from fastapi.responses import RedirectResponse,HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal, engine, Master, BookingInfo, Transport, Schedule, Transport, Bus, Plane, Train
import os
import csv
import io
from datetime import datetime
from fastapi.responses import JSONResponse
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

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/master-form")
def get_master_form(request: Request):
    return templates.TemplateResponse("master.html", {"request": request})

@app.get("/master/")
def get_master_by_its(request: Request, its: int, db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    return templates.TemplateResponse("master.html", {"request": request, "master": master})

@app.get("/mark-as-arrived-form/", response_class=HTMLResponse)
async def get_mark_as_arrived_form(request: Request):
    return templates.TemplateResponse("arrive.html", {"request": request})

@app.post("/mark_as_arrived/", response_class=HTMLResponse)
async def mark_as_arrived(request: Request, its: int = Form(...), db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.ITS == int(its)).first()
    if master:
        master.arrived = 1
        db.commit()
        db.refresh(master)
        return templates.TemplateResponse("arrive.html", {"request": request, "master": master})
    else:
        return templates.TemplateResponse("arrive.html", {"request": request, "error": "No record found for the given ITS"})

@app.post("/master/update", response_class=HTMLResponse)
async def update_master(request: Request,
                        its: int = Form(...),
                        first_name: str = Form(...),
                        middle_name: str = Form(None),
                        last_name: str = Form(...),
                        passport_No: str = Form(...),
                        passport_Expiry: str = Form(...),
                        Visa_No: str = Form(None),
                        db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.ITS == its).first()
    if master:
        master.first_name = first_name
        master.middle_name = middle_name
        master.last_name = last_name
        master.passport_No = passport_No
        master.passport_Expiry = datetime.strptime(passport_Expiry, "%Y-%m-%d").date()
        master.Visa_No = Visa_No
        db.commit()
    return RedirectResponse(url=f"/master?its={its}", status_code=303)

@app.get("/master/info/", response_class=HTMLResponse)
async def get_master_info(its: int = Query(..., description="ITS of the master to retrieve"), db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    return templates.TemplateResponse("master_info.html", {"master": master})

@app.get("/masters/")
def get_masters(request: Request, page: int = 1, db: Session = Depends(get_db)):
    page_size = 10
    masters = db.query(Master).offset((page - 1) * page_size).limit(page_size).all()
    total_masters = db.query(func.count(Master.ITS)).scalar()
    return templates.TemplateResponse("masters.html", {"request": request, "masters": masters, "total_masters": total_masters, "page": page, "page_size": page_size})

   
@app.route("/assign-sim-form", methods=["GET", "POST"])
async def get_assign_sim_form(request: Request, its: int = Form(...)):
    if request.method == "POST":
        db = SessionLocal()
        master = db.query(Master).filter(Master.ITS == its).first()
        if not master:
            raise HTTPException(status_code=404, detail="Master not found")
        return templates.TemplateResponse("assign_sim.html", {"request": request, "master": master})
    else:
        # Handle GET request here (if needed)
        return templates.TemplateResponse("assign_sim.html", {"request": request})

@app.post("/assign-sim/", response_class=HTMLResponse)
async def assign_sim(request: Request, its: int = Form(...), db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    
    db.commit()
    db.refresh(master)
    return templates.TemplateResponse("assign_sim.html", {"request": request, "master": master, "message": "SIM assigned successfully"})

@app.post("/update-phone/", response_class=HTMLResponse)
async def update_phone(request: Request, its: int = Form(...), phone_number: str = Form(...), db: Session = Depends(get_db)):
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


@app.get("/assign-transport-form")
def get_assign_transport_form(request: Request):
    return templates.TemplateResponse("assign_transport.html", {"request": request})

@app.post("/assign-transport/")
def assign_transport(request: Request, its: int = Form(...), transport_id: int = Form(...), db: Session = Depends(get_db)):
    transport = db.query(Transport).filter(Transport.id == transport_id).first()
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    
    booking_info = BookingInfo(
        ITS=its,
        Mode=transport_id,
        Issued=True,
        Departed=False,
        Self_Issued=True
    )
    db.add(booking_info)
    db.commit()
    db.refresh(booking_info)
    return templates.TemplateResponse("assign_transport.html", {"request": request, "booking_info": booking_info, "message": "Transport assigned successfully"})

@app.get("/verify-departure-form")
def get_verify_departure_form(request: Request):
    return templates.TemplateResponse("verify_departure.html", {"request": request})

@app.get("/verify-departure/")
def verify_departure(request: Request, its: int, db: Session = Depends(get_db)):
    booking_info = db.query(BookingInfo).filter(BookingInfo.ITS == its).first()
    if not booking_info:
        raise HTTPException(status_code=404, detail="Booking info not found")
    return templates.TemplateResponse("verify_departure.html", {"request": request, "booking_info": booking_info})

@app.get("/add-transport-form")
def get_add_transport_form(request: Request):
    return templates.TemplateResponse("add_transport.html", {"request": request})

@app.post("/add-transport/")
def add_transport(request: Request, name: str = Form(...), type: str = Form(...), db: Session = Depends(get_db)):
    transport = Transport(name=name, type=type)
    db.add(transport)
    db.commit()
    db.refresh(transport)
    return templates.TemplateResponse("add_transport.html", {"request": request, "message": "Transport added successfully"})

@app.get("/add-schedule-form")
def get_add_schedule_form(request: Request):
    return templates.TemplateResponse("add_schedule.html", {"request": request})

@app.post("/add-schedule/")
def add_schedule(request: Request, transport_id: int = Form(...), departure_time: str = Form(...), arrival_time: str = Form(...), route: str = Form(...), db: Session = Depends(get_db)):
    departure_time = datetime.strptime(departure_time, '%Y-%m-%dT%H:%M')
    arrival_time = datetime.strptime(arrival_time, '%Y-%m-%dT%H:%M')
    schedule = Schedule(transport_id=transport_id, departure_time=departure_time, arrival_time=arrival_time, route=route)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return templates.TemplateResponse("add_schedule.html", {"request": request, "message": "Schedule added successfully"})


@app.get("/view-transport-modes/")
def view_transport_modes(request: Request, db: Session = Depends(get_db)):
    transports = db.query(Transport).all()
    return templates.TemplateResponse("view_transport_modes.html", {"request": request, "transports": transports})

@app.get("/view-buses/")
def view_buses(request: Request, db: Session = Depends(get_db)):
    buses = db.query(Bus).all()
    return templates.TemplateResponse("view_buses.html", {"request": request, "buses": buses})

@app.get("/view-planes/")
def view_planes(request: Request, db: Session = Depends(get_db)):
    planes = db.query(Plane).all()
    return templates.TemplateResponse("view_planes.html", {"request": request, "planes": planes})

@app.get("/view-trains/")
def view_trains(request: Request, db: Session = Depends(get_db)):
    trains = db.query(Train).all()
    return templates.TemplateResponse("view_trains.html", {"request": request, "trains": trains})


@app.get("/add-bus/")
def get_add_bus(request: Request):
    return templates.TemplateResponse("add_bus.html", {"request": request})


@app.post("/add-bus/")
def post_add_bus(request: Request, no_of_seats: int = Form(...), type: str = Form(...), db: Session = Depends(get_db)):
    # Get the highest bus number from the database
    highest_bus_number = int(db.query(func.max(Bus.bus_number)).scalar())
    
    # If there are no buses yet, start from 1, otherwise, increment the highest bus number
    new_bus_number = highest_bus_number + 1 if highest_bus_number else 1
    
    new_bus = Bus(bus_number=new_bus_number, no_of_seats=no_of_seats, type=type)
    db.add(new_bus)
    db.commit()
    return RedirectResponse(url="/view-buses/", status_code=303)

@app.get("/add-train/")
def get_add_train(request: Request):
    return templates.TemplateResponse("add_train.html", {"request": request})

@app.post("/add-train/")
def post_add_train(request: Request, company: str = Form(...), type: str = Form(...), departure_time: str = Form(...), db: Session = Depends(get_db)):
    new_train = Train(company=company, type=type, departure_time=datetime.strptime(departure_time, '%Y-%m-%d').date())
    db.add(new_train)
    db.commit()
    return RedirectResponse(url="/view-trains/", status_code=303)

@app.get("/add-plane/")
def get_add_plane(request: Request):
    return templates.TemplateResponse("add_plane.html", {"request": request})

@app.post("/add-plane/")
def post_add_plane(request: Request, company: str = Form(...), type: str = Form(...), departure_time: str = Form(...), db: Session = Depends(get_db)):
    new_plane = Plane(company=company, type=type, departure_time=datetime.strptime(departure_time, '%Y-%m-%d').date())
    db.add(new_plane)
    db.commit()
    return RedirectResponse(url="/view-planes/", status_code=303)

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

@app.get("/bus-booking/", response_class=HTMLResponse)
async def get_bus_booking(request: Request, its: int = None, db: Session = Depends(get_db)):
    person = db.query(Master).filter(Master.ITS == its).first() if its else None
    return templates.TemplateResponse("bus_booking.html", {"request": request, "person": person, "search": its})

@app.post("/book-bus/", response_class=HTMLResponse)
async def book_bus(request: Request, its: int = Form(...), bus_number: str = Form(...), no_of_seats: int = Form(...), type: str = Form(...), departure_time: str = Form(...), db: Session = Depends(get_db)):
    # Add the bus booking logic here
    new_bus = Bus(bus_number=bus_number, no_of_seats=no_of_seats, type=type)
    db.add(new_bus)
    db.commit()
    booking_info = BookingInfo(
        ITS=its,
        Mode=new_bus.id,
        Issued=True,
        Departed=False,
        Self_Issued=True
    )
    db.add(booking_info)
    db.commit()
    return templates.TemplateResponse("bus_booking.html", {"request": request, "message": "Bus booked successfully!", "person": db.query(Master).filter(Master.ITS == its).first()})


@app.get("/{its}")
def get_master(its: int, db: Session = Depends(get_db)):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
