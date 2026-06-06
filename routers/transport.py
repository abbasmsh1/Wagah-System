from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db, Transport, Bus, Train, Plane, BookingInfo
from datetime import datetime, time

router = APIRouter()

templates = Jinja2Templates(directory="templates")

# Bus routes
@router.get("/bus/add", response_class=HTMLResponse)
async def get_add_bus(request: Request):
    return templates.TemplateResponse("add_bus.html", {"request": request})

@router.post("/bus/add", response_class=HTMLResponse)
async def post_add_bus(
    request: Request,
    no_of_seats: int = Form(...),
    type: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        new_bus = Bus(
            bus_number=(db.query(func.max(Bus.bus_number)).scalar() or 100) + 1,
            no_of_seats=no_of_seats,
            capacity=no_of_seats,  # Transport.capacity is NOT NULL
            type=type,
            available_seats=no_of_seats,
            bus_type=type # Match both inherited and specific field
        )
        db.add(new_bus)
        db.commit()
        return RedirectResponse(url="/transport/bus/list", status_code=303)
    except Exception:
        db.rollback()
        raise

@router.get("/bus/list", response_class=HTMLResponse)
async def list_buses(request: Request, db: Session = Depends(get_db)):
    buses = db.query(Bus).all()
    return templates.TemplateResponse(
        "view_buses.html",
        {"request": request, "buses": buses}
    )

# Train routes
@router.get("/train/add", response_class=HTMLResponse)
async def get_add_train(request: Request):
    return templates.TemplateResponse("add_train.html", {"request": request})

@router.post("/train/add", response_class=HTMLResponse)
async def post_add_train(
    request: Request,
    train_name: str = Form(...),
    train_number: str = Form(...),
    no_of_seats: int = Form(...),
    departure_time: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        departure_time_obj = datetime.strptime(departure_time, "%H:%M").time()
        new_train = Train(
            train_name=train_name,
            train_number=train_number,
            departure_time=departure_time_obj,
            type="train",
            capacity=no_of_seats,
            no_of_seats=no_of_seats,
            available_seats=no_of_seats
        )
        db.add(new_train)
        db.commit()
        return RedirectResponse(url="/transport/train/list", status_code=303)
    except Exception:
        db.rollback()
        raise

@router.get("/train/list", response_class=HTMLResponse)
async def list_trains(request: Request, db: Session = Depends(get_db)):
    trains = db.query(Train).all()
    return templates.TemplateResponse(
        "view_trains.html",
        {"request": request, "trains": trains}
    )

# Plane routes
@router.get("/plane/add", response_class=HTMLResponse)
async def get_add_plane(request: Request):
    return templates.TemplateResponse("add_plane.html", {"request": request})

@router.post("/plane/add", response_class=HTMLResponse)
async def post_add_plane(
    request: Request,
    company: str = Form(...),
    flight_number: str = Form(...),
    no_of_seats: int = Form(...),
    departure_time: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        departure_time_obj = datetime.strptime(departure_time, "%H:%M").time()
        new_plane = Plane(
            company=company,
            flight_number=flight_number,
            departure_time=departure_time_obj,
            type="plane",
            capacity=no_of_seats,
            no_of_seats=no_of_seats,
            available_seats=no_of_seats
        )
        db.add(new_plane)
        db.commit()
        return RedirectResponse(url="/transport/plane/list", status_code=303)
    except Exception:
        db.rollback()
        raise

@router.get("/plane/list", response_class=HTMLResponse)
async def list_planes(request: Request, db: Session = Depends(get_db)):
    planes = db.query(Plane).all()
    return templates.TemplateResponse(
        "view_planes.html",
        {"request": request, "planes": planes}
    )
