from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException
import os

# Assuming the following imports are already present
from database import SessionLocal, BookingInfo, Master

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get('/')
def home( request: Request):
        return templates.TemplateResponse("modify.html", {"request": request})

@app.get('/check_its/')
def get_its(request: Request,its: int, db: Session = Depends(get_db)):
        person = db.query(Master).filter(Master.ITS == its).first()
        booking = db.query(BookingInfo).filter(BookingInfo.ITS == its).first()
        return templates.TemplateResponse("modify.html", {"request": request, "person":person,"booking":booking})
        
        

@app.get('/delete_booking/')
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
        print(booking_id)
        booking = db.query(BookingInfo).filter(BookingInfo.ITS == booking_id).first()
        if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
        
        db.delete(booking)
        db.commit()
        return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 7000)))
