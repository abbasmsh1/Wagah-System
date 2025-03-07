from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from database import SessionLocal, Master, ProcessedMaster
from datetime import datetime

router = APIRouter(
    prefix="/master",
    tags=["master"]
)

templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
async def get_master_form(request: Request):
    return templates.TemplateResponse("master_form.html", {"request": request})

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
    passport_no: str = Form(...),
    passport_expiry: str = Form(...),
    visa_no: str = Form(None),
    db: Session = Depends(get_db)
):
    master = db.query(Master).filter(Master.its == its).first()
    if not master:
        master = Master(
            its=its,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            passport_no=passport_no,
            passport_expiry=datetime.strptime(passport_expiry, "%Y-%m-%d").date(),
            visa_no=visa_no
        )
        db.add(master)
    else:
        master.first_name = first_name
        master.middle_name = middle_name
        master.last_name = last_name
        master.passport_no = passport_no
        master.passport_expiry = datetime.strptime(passport_expiry, "%Y-%m-%d").date()
        master.visa_no = visa_no
    
    try:
        db.commit()
        return RedirectResponse(url=f"/master/info/?its={its}", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
            "total_pages": total_pages
        }
    ) 