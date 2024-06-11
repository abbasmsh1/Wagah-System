from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from database import SessionLocal, User

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)