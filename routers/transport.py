from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from database import SessionLocal, Transport, Bus, Train, Plane, BookingInfo
from datetime import datetime, time

router = APIRouter(
    prefix="/transport",
    tags=["transport"]
)

templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
            no_of_seats=no_of_seats,
            type=type,
            available_seats=no_of_seats
        )
        db.add(new_bus)
        db.commit()
        return RedirectResponse(url="/transport/bus/list", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bus/list", response_class=HTMLResponse)
async def list_buses(request: Request, db: Session = Depends(get_db)):
    buses = db.query(Bus).all()
    return templates.TemplateResponse(
        "bus_list.html",
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
    departure_time: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        departure_time_obj = datetime.strptime(departure_time, "%H:%M").time()
        new_train = Train(
            train_name=train_name,
            departure_time=departure_time_obj
        )
        db.add(new_train)
        db.commit()
        return RedirectResponse(url="/transport/train/list", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/train/list", response_class=HTMLResponse)
async def list_trains(request: Request, db: Session = Depends(get_db)):
    trains = db.query(Train).all()
    return templates.TemplateResponse(
        "train_list.html",
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
    departure_time: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        departure_time_obj = datetime.strptime(departure_time, "%H:%M").time()
        new_plane = Plane(
            company=company,
            departure_time=departure_time_obj
        )
        db.add(new_plane)
        db.commit()
        return RedirectResponse(url="/transport/plane/list", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plane/list", response_class=HTMLResponse)
async def list_planes(request: Request, db: Session = Depends(get_db)):
    planes = db.query(Plane).all()
    return templates.TemplateResponse(
        "plane_list.html",
        {"request": request, "planes": planes}
    ) 