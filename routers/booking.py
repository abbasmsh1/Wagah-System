from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db, BookingInfo, Master, Bus, Train, Plane
from datetime import datetime

router = APIRouter(
    tags=["booking"]
)

templates = Jinja2Templates(directory="templates")

@router.get("/bus/form", response_class=HTMLResponse)
async def get_bus_booking_form(
    request: Request,
    its: int = Query(None),
    db: Session = Depends(get_db)
):
    buses = db.query(Bus).filter(Bus.available_seats > 0).all()
    master = None
    if its:
        master = db.query(Master).filter(Master.its == its).first()
    return templates.TemplateResponse(
        "bus_booking.html",
        {"request": request, "buses": buses, "master": master}
    )

@router.post("/bus/create", response_class=HTMLResponse)
async def create_bus_booking(
    request: Request,
    its: int = Form(...),
    bus_number: int = Form(...),
    db: Session = Depends(get_db)
):
    master = db.query(Master).filter(Master.its == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")

    bus = db.query(Bus).filter(Bus.bus_number == bus_number).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    if bus.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No available seats")

    try:
        booking = BookingInfo(
            its=its,
            mode=1,  # 1 for bus
            transport_id=bus.bus_id,
            booking_time=datetime.now()
        )
        db.add(booking)
        bus.available_seats -= 1
        db.commit()
        return RedirectResponse(url=f"/booking/info/{booking.id}", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/train/form", response_class=HTMLResponse)
async def get_train_booking_form(
    request: Request,
    its: int = Query(None),
    db: Session = Depends(get_db)
):
    trains = db.query(Train).all()
    master = None
    if its:
        master = db.query(Master).filter(Master.its == its).first()
    return templates.TemplateResponse(
        "train_booking.html",
        {"request": request, "trains": trains, "master": master}
    )

@router.post("/train/create", response_class=HTMLResponse)
async def create_train_booking(
    request: Request,
    its: int = Form(...),
    train_id: int = Form(...),
    seat_number: str = Form(...),
    coach_number: str = Form(...),
    cabin_number: str = Form(...),
    db: Session = Depends(get_db)
):
    master = db.query(Master).filter(Master.its == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")

    train = db.query(Train).filter(Train.id == train_id).first()
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")

    if train.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No available seats")

    try:
        booking = BookingInfo(
            its=its,
            mode=2,  # 2 for train
            transport_id=train_id,
            seat_number=seat_number,
            coach_number=coach_number,
            cabin_number=cabin_number,
            booking_time=datetime.now()
        )
        db.add(booking)
        train.available_seats -= 1
        db.commit()
        return RedirectResponse(url=f"/booking/info/{booking.id}", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plane/form", response_class=HTMLResponse)
async def get_plane_booking_form(
    request: Request,
    its: int = Query(None),
    db: Session = Depends(get_db)
):
    planes = db.query(Plane).all()
    master = None
    if its:
        master = db.query(Master).filter(Master.its == its).first()
    return templates.TemplateResponse(
        "plane_booking.html",
        {"request": request, "planes": planes, "master": master}
    )

@router.post("/plane/create", response_class=HTMLResponse)
async def create_plane_booking(
    request: Request,
    its: int = Form(...),
    plane_id: int = Form(...),
    seat_number: str = Form(...),
    db: Session = Depends(get_db)
):
    master = db.query(Master).filter(Master.its == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")

    plane = db.query(Plane).filter(Plane.id == plane_id).first()
    if not plane:
        raise HTTPException(status_code=404, detail="Plane not found")

    if plane.available_seats <= 0:
        raise HTTPException(status_code=400, detail="No available seats")

    try:
        booking = BookingInfo(
            its=its,
            mode=3,  # 3 for plane
            transport_id=plane_id,
            seat_number=seat_number,
            booking_time=datetime.now()
        )
        db.add(booking)
        plane.available_seats -= 1
        db.commit()
        return RedirectResponse(url=f"/booking/info/{booking.id}", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info/{booking_id}", response_class=HTMLResponse)
async def get_booking_info(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db)
):
    booking = db.query(BookingInfo).filter(BookingInfo.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    master = db.query(Master).filter(Master.its == booking.its).first()
    transport = None

    if booking.mode == 1:
        transport = db.query(Bus).filter(Bus.bus_id == booking.transport_id).first()
    elif booking.mode == 2:
        transport = db.query(Train).filter(Train.train_id == booking.transport_id).first()
    elif booking.mode == 3:
        transport = db.query(Plane).filter(Plane.plane_id == booking.transport_id).first()

    return templates.TemplateResponse(
        "booking_info.html",
        {
            "request": request,
            "booking": booking,
            "master": master,
            "transport": transport
        }
    )
