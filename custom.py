from fastapi import FastAPI, Depends, Request, Form, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, Master, ProcessedMaster, User
import os
from datetime import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

group_numbers = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login/")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password == password:
        response = RedirectResponse(url="/master-form/", status_code=303)
        response.set_cookie(key="username", value=username)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})

@app.get("/logout/")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("username")
    return response

def get_current_user(request: Request, db: Session = Depends(get_db)):
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/master-form/")
def get_master_form(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.designation.lower() in ["admin", "custom"]:
        processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()
        return templates.TemplateResponse("master_.html", {"request": request, "processedCount": processed_count})
    raise HTTPException(status_code=403, detail="Not authorized")

@app.get("/master/")
def get_master_by_its(request: Request, its: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        return templates.TemplateResponse("master_.html", {"request": request, "error": "Master not found"})
    processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()
    return templates.TemplateResponse("master_.html", {"request": request, "master": master, "processedCount": processed_count})

@app.get("/master/check-duplicate")
def check_duplicate(its: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    is_duplicate = db.query(ProcessedMaster).filter(ProcessedMaster.ITS == its, ProcessedMaster.processed_by == current_user.username).count() > 0
    return JSONResponse(content={'isDuplicate': is_duplicate})

@app.post("/master/update", response_class=HTMLResponse)
async def update_master(
    request: Request,
    its: int = Form(...),
    first_name: str = Form(...),
    middle_name: str = Form(None),
    last_name: str = Form(...),
    passport_No: str = Form(...),
    passport_Expiry: str = Form(...),
    Visa_No: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_duplicate = db.query(ProcessedMaster).filter(ProcessedMaster.ITS == its, ProcessedMaster.processed_by == current_user.username).count() > 0
    if is_duplicate:
        processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()
        return templates.TemplateResponse("master_.html", {"request": request, "error": "Record already processed", "processedCount": processed_count})

    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        return templates.TemplateResponse("master_.html", {"request": request, "error": "Master not found"})

    try:
        master.first_name = first_name
        master.middle_name = middle_name
        master.last_name = last_name
        master.passport_No = passport_No
        master.passport_Expiry = datetime.strptime(passport_Expiry, "%Y-%m-%d").date()
        master.Visa_No = Visa_No

        db.commit()

        processed_master = ProcessedMaster(
            ITS=master.ITS,
            first_name=master.first_name,
            middle_name=master.middle_name,
            last_name=master.last_name,
            DOB=master.DOB,
            passport_No=master.passport_No,
            passport_Expiry=master.passport_Expiry,
            Visa_No=master.Visa_No,
            Mode_of_Transport=master.Mode_of_Transport,
            phone=master.phone,
            arrived=master.arrived,
            timestamp=master.timestamp,
            processed_by=current_user.username
        )
        db.add(processed_master)
        db.commit()

        processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()

        if processed_count >= 10:
            return await print_processed_its(request, current_user, db)  # Pass db to print_processed_its

    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse("master_.html", {"request": request, "error": "Record already exists"})

    processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()
    return templates.TemplateResponse("master_.html", {"request": request, "processedCount": processed_count})

@app.get("/master/info/", response_class=HTMLResponse)
async def get_master_info(request: Request, its: int = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        return templates.TemplateResponse("master_.html", {"request": request, "error": "Master not found"})
    processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()
    return templates.TemplateResponse("master_.html", {"request": request, "master": master, "processedCount": processed_count})

@app.get("/print-processed-its/", response_class=HTMLResponse)
async def print_processed_its(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    global group_numbers

    if current_user.username not in group_numbers:
        group_numbers[current_user.username] = max(group_numbers.values(), default=0) + 1

    processed_entries = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).all()

    response_content = f"""
    <html>
        <head>
            <title>Processed ITS Entries</title>
        </head>
        <body>
            <h2>Processed ITS Entries</h2>
            <h3>Group Number: {group_numbers[current_user.username]}</h3>
            <table border="1">
                <thead>
                    <tr>
                        <th>ITS</th>
                        <th>Name</th>
                        <th>Passport Number</th>
                        <th>Visa Number</th>
                    </tr>
                </thead>
                <tbody>
    """
    for entry in processed_entries:
        response_content += f"""
        <tr>
            <td>{entry.ITS}</td>
            <td>{entry.first_name} {entry.last_name}</td>
            <td>{entry.passport_No}</td>
            <td>{entry.Visa_No}</td>
        </tr>
        """
    response_content += """
                </tbody>
            </table>
        </body>
    </html>
    """

    # Clear processed entries for the user after printing
    db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).delete()
    db.commit()

    return HTMLResponse(content=response_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 1000)))
