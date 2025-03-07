from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Any
from database import SessionLocal, Master, BookingInfo, Bus, Train, Plane, User, ProcessedMaster
from middleware.auth import admin_required
import json

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def calculate_growth(current: int, previous: int) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)

def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    # Get current timestamp and last week's timestamp
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    yesterday = now - timedelta(days=1)

    # Calculate total masters and growth
    total_masters = db.query(func.count(Master.ITS)).scalar()
    masters_last_week = db.query(func.count(Master.ITS)).filter(Master.timestamp < week_ago).scalar()
    masters_growth = calculate_growth(total_masters, masters_last_week)

    # Calculate active bookings and growth
    active_bookings = db.query(func.count(BookingInfo.id)).filter(BookingInfo.Departed == False).scalar()
    bookings_last_week = db.query(func.count(BookingInfo.id)).filter(
        BookingInfo.booking_time < week_ago,
        BookingInfo.Departed == False
    ).scalar()
    bookings_growth = calculate_growth(active_bookings, bookings_last_week)

    # Calculate available transport
    available_buses = db.query(func.count(Bus.id)).filter(Bus.available_seats > 0).scalar()
    available_trains = db.query(func.count(Train.id)).scalar()
    available_planes = db.query(func.count(Plane.id)).scalar()
    available_transport = available_buses + available_trains + available_planes

    # Calculate processed today and trend
    processed_today = db.query(func.count(ProcessedMaster.id)).filter(
        func.date(ProcessedMaster.timestamp) == func.date(now)
    ).scalar()
    processed_yesterday = db.query(func.count(ProcessedMaster.id)).filter(
        func.date(ProcessedMaster.timestamp) == func.date(yesterday)
    ).scalar()
    processing_trend = calculate_growth(processed_today, processed_yesterday)

    # Calculate transport distribution
    bus_bookings = db.query(func.count(BookingInfo.id)).filter(BookingInfo.Mode == 1).scalar()
    train_bookings = db.query(func.count(BookingInfo.id)).filter(BookingInfo.Mode == 2).scalar()
    plane_bookings = db.query(func.count(BookingInfo.id)).filter(BookingInfo.Mode == 3).scalar()

    return {
        "total_masters": total_masters,
        "masters_growth": masters_growth,
        "active_bookings": active_bookings,
        "bookings_growth": bookings_growth,
        "available_transport": available_transport,
        "available_buses": available_buses,
        "available_trains": available_trains,
        "available_planes": available_planes,
        "processed_today": processed_today,
        "processing_trend": processing_trend,
        "bus_bookings": bus_bookings,
        "train_bookings": train_bookings,
        "plane_bookings": plane_bookings
    }

def get_chart_data(db: Session) -> Dict[str, Any]:
    # Get bookings trend for the last 7 days
    now = datetime.now()
    dates = [(now - timedelta(days=i)).date() for i in range(6, -1, -1)]
    
    bookings_data = []
    for date in dates:
        count = db.query(func.count(BookingInfo.id)).filter(
            func.date(BookingInfo.booking_time) == date
        ).scalar()
        bookings_data.append(count)

    return {
        "bookings_trend": {
            "labels": [date.strftime("%Y-%m-%d") for date in dates],
            "data": bookings_data
        }
    }

def get_recent_activity(db: Session, limit: int = 10) -> list:
    # Get recent processed masters
    processed = db.query(ProcessedMaster).order_by(ProcessedMaster.timestamp.desc()).limit(limit).all()
    
    activities = []
    for p in processed:
        activities.append({
            "timestamp": p.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "Master Processed",
            "user": p.processed_by,
            "details": f"ITS: {p.ITS}"
        })
    
    return activities

@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(admin_required)
):
    stats = get_dashboard_stats(db)
    chart_data = get_chart_data(db)
    recent_activity = get_recent_activity(db)
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "stats": stats,
            "chart_data": chart_data,
            "recent_activity": recent_activity
        }
    )

@router.get("/masters", response_class=HTMLResponse)
async def admin_masters(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    _: bool = Depends(admin_required)
):
    page_size = 20
    offset = (page - 1) * page_size
    
    masters = db.query(Master).offset(offset).limit(page_size).all()
    total = db.query(func.count(Master.ITS)).scalar()
    total_pages = (total + page_size - 1) // page_size
    
    return templates.TemplateResponse(
        "admin/masters.html",
        {
            "request": request,
            "masters": masters,
            "page": page,
            "total_pages": total_pages
        }
    )

@router.get("/bookings", response_class=HTMLResponse)
async def admin_bookings(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    _: bool = Depends(admin_required)
):
    page_size = 20
    offset = (page - 1) * page_size
    
    bookings = db.query(BookingInfo).offset(offset).limit(page_size).all()
    total = db.query(func.count(BookingInfo.id)).scalar()
    total_pages = (total + page_size - 1) // page_size
    
    return templates.TemplateResponse(
        "admin/bookings.html",
        {
            "request": request,
            "bookings": bookings,
            "page": page,
            "total_pages": total_pages
        }
    )

@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(admin_required)
):
    users = db.query(User).all()
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "users": users
        }
    ) 