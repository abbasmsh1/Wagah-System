from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Any
from database import get_db, Master, BookingInfo, Bus, Train, Plane, User, ProcessedMaster
from config.security import get_password_hash, validate_password
from middleware.auth import admin_required

router = APIRouter()

templates = Jinja2Templates(directory="templates")

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
    total_masters = db.query(func.count(Master.its)).scalar()
    masters_last_week = db.query(func.count(Master.its)).filter(Master.timestamp < week_ago).scalar()
    masters_growth = calculate_growth(total_masters, masters_last_week)

    # Calculate active bookings and growth
    active_bookings = db.query(func.count(BookingInfo.id)).filter(BookingInfo.departed == False).scalar()
    bookings_last_week = db.query(func.count(BookingInfo.id)).filter(
        BookingInfo.booking_time < week_ago,
        BookingInfo.departed == False
    ).scalar()
    bookings_growth = calculate_growth(active_bookings, bookings_last_week)

    # Calculate available transport
    available_buses = db.query(func.count(Bus.bus_id)).filter(Bus.available_seats > 0).scalar()
    available_trains = db.query(func.count(Train.train_id)).scalar()
    available_planes = db.query(func.count(Plane.plane_id)).scalar()
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
    bus_bookings = db.query(func.count(BookingInfo.id)).filter(BookingInfo.mode == 1).scalar()
    train_bookings = db.query(func.count(BookingInfo.id)).filter(BookingInfo.mode == 2).scalar()
    plane_bookings = db.query(func.count(BookingInfo.id)).filter(BookingInfo.mode == 3).scalar()

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
            "user": p.processed_by_username,
            "details": f"ITS: {p.its}"
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
    total = db.query(func.count(Master.its)).scalar()
    total_pages = (total + page_size - 1) // page_size

    return templates.TemplateResponse(
        "masters.html",
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
        "view_booking_info.html",
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

VALID_ROLES = ("admin", "staff", "user")

@router.get("/users/add", response_class=HTMLResponse)
async def add_user_form(
    request: Request,
    _: bool = Depends(admin_required)
):
    return templates.TemplateResponse("admin/add_user.html", {"request": request})

@router.post("/users/add", response_class=HTMLResponse)
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    designation: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
    _: bool = Depends(admin_required)
):
    if role not in VALID_ROLES:
        role = "user"
    if not validate_password(password):
        return templates.TemplateResponse(
            "admin/add_user.html",
            {"request": request, "message": "Password must be at least 8 characters and "
             "include upper- and lower-case letters, a digit and a special character."},
            status_code=400,
        )
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(
            "admin/add_user.html",
            {"request": request, "message": "That username already exists."},
            status_code=400,
        )
    user = User(
        username=username,
        hashed_password=get_password_hash(password),
        role=role,
        designation=designation,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

@router.post("/users/{user_id}/toggle", response_class=HTMLResponse)
async def toggle_user_active(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Don't let an admin lock themselves out of the last active admin account.
    if user.role == "admin" and user.is_active:
        active_admins = db.query(func.count(User.id)).filter(
            User.role == "admin", User.is_active == True
        ).scalar()
        if active_admins <= 1:
            raise HTTPException(status_code=400, detail="Cannot deactivate the last active admin")
    user.is_active = not user.is_active
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)
