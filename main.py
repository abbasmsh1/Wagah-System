from fastapi import FastAPI, Depends, HTTPException, Request, Form, File, UploadFile, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import csv
from database import SessionLocal, Master, Group, GroupInfo, BookingInfo
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

class MasterCreate(BaseModel):
    ITS: int
    first_name: str
    middle_name: str
    last_name: str
    email: str
    DOB: str  # Pydantic can parse date strings
    passport_No: str
    passport_Issue: str
    passport_Expiry: str
    Visa_No: str
    Mode_of_Transport: str

class MasterResponse(MasterCreate):
    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/masters/", response_model=MasterResponse)
def create_master(master: MasterCreate, db: Session = Depends(get_db)):
    db_master = Master(**master.dict())
    db.add(db_master)
    db.commit()
    db.refresh(db_master)
    return db_master

@app.get("/masters/", response_model=List[MasterResponse])
def read_masters(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    masters = db.query(Master).offset(skip).limit(limit).all()
    return masters

@app.get("/masters/{its_id}", response_model=MasterResponse)
def read_master(its_id: int, db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.ITS == its_id).first()
    if master is None:
        raise HTTPException(status_code=404, detail="Master not found")
    return master

@app.put("/masters/{its_id}", response_model=MasterResponse)
def update_master(its_id: int, master: MasterCreate, db: Session = Depends(get_db)):
    db_master = db.query(Master).filter(Master.ITS == its_id).first()
    if db_master is None:
        raise HTTPException(status_code=404, detail="Master not found")
    for key, value in master.dict().items():
        setattr(db_master, key, value)
    db.commit()
    db.refresh(db_master)
    return db_master

@app.delete("/masters/{its_id}")
def delete_master(its_id: int, db: Session = Depends(get_db)):
    db_master = db.query(Master).filter(Master.ITS == its_id).first()
    if db_master is None:
        raise HTTPException(status_code=404, detail="Master not found")
    db.delete(db_master)
    db.commit()
    return {"detail": "Master deleted"}

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
def search_user_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/search/{its_id}", response_class=HTMLResponse)
def search_master(request: Request, its_id: int, db: Session = Depends(get_db)):
    master = db.query(Master).filter(Master.ITS == its_id).first()
    if master is None:
        return templates.TemplateResponse("search.html", {"request": request, "error": "Master not found"})
    return templates.TemplateResponse("user_details.html", {"request": request, "master": master})

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
def upload_master(request: Request, ITS: int = Form(...), first_name: str = Form(...), middle_name: str = Form(...), last_name: str = Form(...), email: str = Form(...), DOB: str = Form(...), passport_No: str = Form(...), passport_Issue: str = Form(...), passport_Expiry: str = Form(...), Visa_No: str = Form(...), Mode_of_Transport: str = Form(...), db: Session = Depends(get_db)):
    db_master = Master(
        ITS=ITS,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        email=email,
        DOB=DOB,
        passport_No=passport_No,
        passport_Issue=passport_Issue,
        passport_Expiry=passport_Expiry,
        Visa_No=Visa_No,
        Mode_of_Transport=Mode_of_Transport
    )
    db.add(db_master)
    db.commit()
    db.refresh(db_master)
    return templates.TemplateResponse("user_details.html", {"request": request, "master": db_master})

@app.get("/upload_csv", response_class=HTMLResponse)
def upload_csv_page(request: Request):
    return templates.TemplateResponse("upload_csv.html", {"request": request})

@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    content = content.decode("utf-8").splitlines()
    csv_reader = csv.reader(content)
    headers = next(csv_reader)  # Skip header row
    for row in csv_reader:
        master_data = {
            "ITS": int(row[0]),
            "first_name": row[1],
            "middle_name": row[2],
            "last_name": row[3],
            "email": row[4],
            "DOB": row[5],
            "passport_No": row[6],
            "passport_Issue": row[7],
            "passport_Expiry": row[8],
            "Visa_No": row[9],
            "Mode_of_Transport": row[10]
        }
        db_master = Master(**master_data)
        db.add(db_master)
    db.commit()
    return {"detail": "Masters uploaded successfully"}

@app.get("/masters_paginated", response_class=HTMLResponse)
def masters_paginated(request: Request, page: int = Query(1, alias='page'), db: Session = Depends(get_db)):
    limit = 10
    skip = (page - 1) * limit
    masters = db.query(Master).offset(skip).limit(limit).all()
    total_masters = db.query(Master).count()
    total_pages = (total_masters // limit) + (1 if total_masters % limit > 0 else 0)
    return templates.TemplateResponse("users_paginated.html", {"request": request, "masters": masters, "page": page, "total_pages": total_pages})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=int(os.getenv("PORT", 8000)))
