from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db, Master
from datetime import datetime

router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def get_master_form(request: Request):
    return templates.TemplateResponse("master.html", {"request": request})

@router.get("/info/", response_class=HTMLResponse)
async def get_master_info(
    request: Request,
    its: int = Query(..., description="ITS of the master to retrieve"),
    db: Session = Depends(get_db)
):
    master = db.query(Master).filter(Master.its == its).first()
    if not master:
        raise HTTPException(status_code=404, detail="Master not found")
    return templates.TemplateResponse(
        "master_info.html",
        {"request": request, "master": master}
    )

@router.post("/update", response_class=HTMLResponse)
async def update_master(
    request: Request,
    its: int = Form(...),
    first_name: str = Form(...),
    middle_name: str = Form(None),
    last_name: str = Form(...),
    date_of_birth: str = Form(...),
    passport_number: str = Form(...),
    passport_expiry: str = Form(...),
    visa_number: str = Form(...),
    mode_of_transport: str = Form(...),
    phone: str = Form(None),
    db: Session = Depends(get_db)
):
    if mode_of_transport not in ("bus", "train", "plane"):
        raise HTTPException(status_code=400, detail="Invalid mode of transport")
    dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    expiry = datetime.strptime(passport_expiry, "%Y-%m-%d").date()

    master = db.query(Master).filter(Master.its == its).first()
    if not master:
        master = Master(
            its=its,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            date_of_birth=dob,
            passport_number=passport_number,
            passport_expiry=expiry,
            visa_number=visa_number,
            mode_of_transport=mode_of_transport,
            phone=phone,
        )
        db.add(master)
    else:
        master.first_name = first_name
        master.middle_name = middle_name
        master.last_name = last_name
        master.date_of_birth = dob
        master.passport_number = passport_number
        master.passport_expiry = expiry
        master.visa_number = visa_number
        master.mode_of_transport = mode_of_transport
        master.phone = phone

    try:
        db.commit()
        return RedirectResponse(url=f"/master/info/?its={its}", status_code=303)
    except Exception:
        db.rollback()
        raise

@router.get("/list/", response_class=HTMLResponse)
async def list_masters(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    page_size = 20
    offset = (page - 1) * page_size

    masters = db.query(Master).offset(offset).limit(page_size).all()
    total = db.query(Master).count()
    total_pages = (total + page_size - 1) // page_size

    return templates.TemplateResponse(
        "masters_list.html",
        {
            "request": request,
            "masters": masters,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        }
    )
