import warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, Depends, Request, Form, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, Master, ProcessedMaster, User
import os
from sqlalchemy import func
from datetime import datetime
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ValidationError
from collections import defaultdict

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def compress_its(its: int) -> str:
    try:
        its = str(its)
        if len(its) == 12:
            indices = [6, 5, 2, 7, 4, 0, 9, 8]
            compressed_its = ''.join(its[i] for i in indices)
            return int(compressed_its)
        elif len(its) == 8:
            return int(its)
        else:
            print("Error")
    except:
        return its

group_numbers = {}
local_cache = defaultdict(list)

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
    its = compress_its(its)
    master = db.query(Master).filter(Master.ITS == its).first()
    if not master:
        return templates.TemplateResponse("master_.html", {"request": request, "error": "Master not found"})
    processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()
    return templates.TemplateResponse("master_.html", {"request": request, "master": master, "processedCount": processed_count})

@app.get("/master/check-duplicate")
def check_duplicate(its: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    its = compress_its(its)
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
    its = compress_its(its)
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

        local_cache[current_user.username].append({
            "ITS": master.ITS,
            "first_name": master.first_name,
            "middle_name": master.middle_name,
            "last_name": master.last_name,
            "DOB": master.DOB,
            "passport_No": master.passport_No,
            "passport_Expiry": master.passport_Expiry,
            "Visa_No": master.Visa_No,
            "Mode_of_Transport": master.Mode_of_Transport,
            "phone": master.phone,
            "arrived": master.arrived,
            "timestamp": master.timestamp,
            "processed_by": current_user.username
        })

        response = RedirectResponse(url="/master/", status_code=303)
        response.set_cookie(key="local_cache", value=dict(local_cache))
        response.set_cookie(key="cache_count", value=len(local_cache[current_user.username]))

        processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()

        if len(local_cache[current_user.username]) >= 10:
            return await print_processed_its(request, current_user, db)

    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse("master_.html", {"request": request, "error": "Record already exists"})

    processed_count = db.query(ProcessedMaster).filter(ProcessedMaster.processed_by == current_user.username).count()
    return templates.TemplateResponse("master_.html", {"request": request, "processedCount": processed_count})

@app.get("/cache-count/")
async def cache_count(request: Request):
    cache_count = request.cookies.get("cache_count", 0)
    return JSONResponse(content={"cache_count": cache_count})

@app.get("/master/info/", response_class=HTMLResponse)
async def get_master_info(request: Request, its: int = Query(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    its = compress_its(its)
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

    processed_entries = local_cache[current_user.username]

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
                        <th>First Name</th>
                        <th>Middle Name</th>
                        <th>Last Name</th>
                        <th>Passport No</th>
                        <th>Visa No</th>
                    </tr>
                </thead>
                <tbody>
    """

    for entry in processed_entries:
        response_content += f"""
        <tr>
            <td>{entry['ITS']}</td>
            <td>{entry['first_name']}</td>
            <td>{entry['middle_name']}</td>
            <td>{entry['last_name']}</td>
            <td>{entry['passport_No']}</td>
            <td>{entry['Visa_No']}</td>
        </tr>
        """

    response_content += """
                </tbody>
            </table>
        </body>
    </html>
    """

    local_cache[current_user.username].clear()

    return HTMLResponse(content=response_content)

PAGE_SIZE = 10

@app.get("/processed-masters/", response_class=HTMLResponse)
async def get_processed_masters(
    request: Request,
    page: int = 1,
    user: str = None,  # Accept username from query parameter
    db: Session = Depends(get_db)
):
    users = db.query(User).all()
    total_count = db.query(func.count(ProcessedMaster.ITS)).scalar()

    # Base query for processed masters
    query = db.query(ProcessedMaster)

    # Apply username filter if username is provided
    if user:
        query = query.filter(ProcessedMaster.processed_by == user)

    # Retrieve processed masters for the current page
    processed_masters = (
        query.offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return templates.TemplateResponse(
        "processed_masters_.html",
        {
            "request": request,
            "processed_masters": processed_masters,
            "page": page,
            "page_size": PAGE_SIZE,
            "total_count": total_count,
            "users": users,
            "selected_user": user,  # Pass the selected username to the template
        }
    )

@app.get("/add-master/")
def add_master_form(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("add_master.html", {"request": request})

@app.post("/master/add/", response_class=HTMLResponse)
async def add_master(
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
    its = compress_its(its)
    try:
        master = db.query(Master).filter(Master.ITS == its).first()
    except:
        master = None
        print("not found")
    if master:
        return templates.TemplateResponse("add_master.html", {"request": request, "error": "Master record already exists"})
    
    try:
        new_master = Master(
            ITS=its,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            passport_No=passport_No,
            passport_Expiry=datetime.strptime(passport_Expiry, "%Y-%m-%d").date(),
            Visa_No=Visa_No
        )
        db.add(new_master)
        db.commit()
        return templates.TemplateResponse("add_master.html", {"request": request, "success": "Master record added successfully"})
    except IntegrityError as e:
        db.rollback()
        print(e)
        return templates.TemplateResponse("add_master.html", {"request": request, "error": "Error adding master record"})


@app.get("/print", response_class=HTMLResponse)
async def print_processed_masters(
    request: Request,
    user: str = Query(None),
    page: int = Query(1),
    db: Session = Depends(get_db)
):
    query = db.query(ProcessedMaster)
    if user:
        query = query.filter(ProcessedMaster.processed_by == user)
    
    processed_masters = query.offset((page - 1) * 10).limit(10).all()
    
    context = {
        "request": request,
        "processed_masters": processed_masters,
        "now": datetime.now()  # Include current timestamp in the context
    }
    return templates.TemplateResponse("print_template.html", context)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 1000)))
