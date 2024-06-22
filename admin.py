import warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from database import SessionLocal, User
from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ValidationError

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Function to retrieve all users from the database
def get_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return users
    finally:
        db.close()


# Function to add a new user to the database
def add_user(username: str, password: str, designation: str):
    db = SessionLocal()
    try:
        new_user = User(username=username, password=password, designation=designation)
        db.add(new_user)
        db.commit()
        db.close()
        return True, "User added successfully"
    except Exception as e:
        db.rollback()
        db.close()
        return False, f"Failed to add user: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def render_add_user_form(request: Request, message: str = None):
    return templates.TemplateResponse("add_user.html", {"request": request, "message": message})

# Route to handle the form submission and add the new user to the database
@app.post("/add_user/")
async def add_new_user(request: Request, username: str = Form(...), password: str = Form(...), designation: str = Form(...)):
    success, message = add_user(username, password, designation)
    if success:
        return templates.TemplateResponse("add_user.html", {"request": request, "message": message})
    else:
        return templates.TemplateResponse("add_user.html", {"request": request, "message": message}, status_code=400)

# Route to display all users
@app.get("/users/", response_class=HTMLResponse)
async def display_users(request: Request):
    users = get_users()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})


# async def http_exception_handler(request: Request, exc: HTTPException):
#     if exc.status_code == 404:
#         return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
#     return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

# @app.exception_handler(Exception)
# async def general_exception_handler(request: Request, exc: Exception):
#     return templates.TemplateResponse("500.html", {"request": request}, status_code=500)

# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

# # Middleware to catch all other 404 errors
# @app.middleware("http")
# async def custom_404_handler(request: Request, call_next):
#     response = await call_next(request)
#     if response.status_code == 404:
#         return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
#     return response

# # Fallback route for undefined paths
# @app.get("/{full_path:path}")
# async def fallback_404(request: Request):
#     return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9630)