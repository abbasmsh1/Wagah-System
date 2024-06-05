# main.py
from fastapi import FastAPI, Depends, HTTPException, Request, Form, File, UploadFile, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import csv
from database import SessionLocal, User
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

class UserCreate(BaseModel):
    name: str
    email: str
    age: int

class UserResponse(UserCreate):
    id: int

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(name=user.name, email=user.email, age=user.age)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.name = user.name
    db_user.email = user.email
    db_user.age = user.age
    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"detail": "User deleted"}

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search", response_class=HTMLResponse)
def search_user_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/search/{user_id}", response_class=HTMLResponse)
def search_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return templates.TemplateResponse("search.html", {"request": request, "error": "User not found"})
    return templates.TemplateResponse("user_details.html", {"request": request, "user": user})

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
def upload_user(request: Request, name: str = Form(...), email: str = Form(...), age: int = Form(...), db: Session = Depends(get_db)):
    db_user = User(name=name, email=email, age=age)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return templates.TemplateResponse("user_details.html", {"request": request, "user": db_user})

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
        name, email, age = row
        db_user = User(name=name, email=email, age=int(age))
        db.add(db_user)
    db.commit()
    return {"detail": "Users uploaded successfully"}

@app.get("/users_paginated", response_class=HTMLResponse)
def users_paginated(request: Request, page: int = Query(1, alias='page'), db: Session = Depends(get_db)):
    limit = 10
    skip = (page - 1) * limit
    users = db.query(User).offset(skip).limit(limit).all()
    total_users = db.query(User).count()
    total_pages = (total_users // limit) + (1 if total_users % limit > 0 else 0)
    return templates.TemplateResponse("users_paginated.html", {"request": request, "users": users, "page": page, "total_pages": total_pages})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=int(os.getenv("PORT", 8000)))
