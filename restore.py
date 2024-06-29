import warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
import os
import logging
import threading
import sqlalchemy
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DateTime, Time
from sqlalchemy.sql import func
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


BACKUP_FOLDER = "backups"
# Load environment variables
load_dotenv()

# Get the database URL from the environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    DATABASE_URL = "sqlite:///./test.db"
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for the models
Base = declarative_base()

# Define the Master model
class Master(Base):
    __tablename__ = "master"
    ITS = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)
    DOB = Column(Date)
    passport_No = Column(String, unique=True)
    passport_Expiry = Column(Date)
    Visa_No = Column(String, unique=True)
    Mode_of_Transport = Column(String)
    phone = Column(String, nullable=True)
    arrived = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=func.now())

# Define the Transport base model
class Transport(Base):
    __tablename__ = "transport"
    id = Column(Integer, primary_key=True, index=True)
    departure_time = Column(Time, nullable=True)
    type = Column(String, nullable=False)
    transport_type = Column(String, nullable=False)

    __mapper_args__ = {
        'polymorphic_on': transport_type,
        'polymorphic_identity': 'transport'
    }

# Define the Bus model
class Bus(Transport):
    __tablename__ = "bus"
    bus_id = Column(Integer, ForeignKey('transport.id'), primary_key=True)
    bus_number = Column(Integer, nullable=False)
    no_of_seats = Column(Integer, nullable=False)
    type = Column(String, index=True, nullable=True)
    __mapper_args__ = {
        'polymorphic_identity': 'bus',
    }

# Define the Plane model
class Plane(Base):
    __tablename__ = "plane"
    plane_id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String, nullable=True)
    departure_time = Column(Time, nullable=False)

# Define the Train model
class Train(Base):
    __tablename__ = "train"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    train_name = Column(String, nullable=False)
    departure_time = Column(Time, nullable=False)

# Define the BookingInfo model
class BookingInfo(Base):
    __tablename__ = "booking_info"
    Mode = Column(Integer, index=True)
    ITS = Column(Integer, ForeignKey('master.ITS'), primary_key=True, index=True)
    Issued = Column(Boolean)
    Departed = Column(Boolean)
    Self_Issued = Column(Boolean, default=False)
    seat_number = Column(String)
    bus_number = Column(Integer)
    train_id = Column(Integer, ForeignKey("train.id"), nullable=True)
    plane_id = Column(Integer, ForeignKey("plane.plane_id"), nullable=True)
    coach_number = Column(String)
    cabin_number = Column(String)

    @staticmethod
    def fill_form(db_session: Session, its: int, seat_number: int, bus_number: int):
        """
        Fill the booking form and update the BookingInfo table.
        """
        try:
            # Check if the ITS exists in the Master table
            master_record = db_session.query(Master).filter(Master.ITS == its).first()
            if not master_record:
                return None  # Return None if ITS doesn't exist
            
            # Update the BookingInfo table
            booking_info = BookingInfo(
                Mode=1,  # Update Mode according to your requirements
                ITS=its,
                Issued=True,  # Assuming the form submission indicates the booking is issued
                Departed=False,  # Assuming the bus hasn't departed yet
                Self_Issued=True,  # Assuming the booking is self-issued
                seat_number=seat_number,  # Add seat number to the record
                bus_number=bus_number  # Add bus number to the record
            )
            db_session.add(booking_info)
            db_session.commit()
            return booking_info
        except Exception as e:
            print(f"Error filling form and updating BookingInfo table: {e}")
            db_session.rollback()
            return None

# Define the User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    designation = Column(String)
    
# Define the ProcessedMaster model
class ProcessedMaster(Base):
    __tablename__ = "processed_master"
    id = Column(Integer, primary_key=True, index=True)
    ITS = Column(Integer, ForeignKey('master.ITS'), unique=True, index=True)
    first_name = Column(String, index=True)
    middle_name = Column(String, index=True)
    last_name = Column(String, index=True)
    DOB = Column(Date)
    passport_No = Column(String, index=True)
    passport_Expiry = Column(Date, index=True)
    Visa_No = Column(String, index=True)
    Mode_of_Transport = Column(String, index=True)
    phone = Column(String, index=True)
    arrived = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=func.now())
    processed_by = Column(String, ForeignKey('users.username'))

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# Helper function to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <html>
        <body>
            <h1>Welcome to the Wagah System</h1>
        </body>
    </html>
    """

@app.get("/recover", response_class=HTMLResponse)
async def recover_form():
    backup_files = os.listdir(BACKUP_FOLDER)
    files_options = "".join([f'<option value="{file}">{file}</option>' for file in backup_files])
    return f"""
    <html>
        <body>
            <h1>Recover Data from Backup</h1>
            <form action="/recover" method="post">
                <label for="backupFile">Select backup file:</label>
                <select name="backupFile" id="backupFile">
                    {files_options}
                </select>
                <label for="table">Enter table name (leave blank to restore all):</label>
                <input type="text" id="table" name="table">
                <button type="submit">Recover</button>
            </form>
        </body>
    </html>
    """

@app.post("/recover")
async def recover(backupFile: str = Form(...), table: str = Form(None), db: Session = Depends(get_db)):
    file_path = os.path.join(BACKUP_FOLDER, backupFile)
    try:
        restore_backup(file_path, table, db)
        return {"info": f"File '{backupFile}' restored successfully"}
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def restore_backup(file_path: str, table_name: str, db: Session):
    with open(file_path, 'r') as f:
        sql_script = f.read()
    print(Base.metadata.tables[table_name])
    statements = sql_script.split(';')
    for statement in statements:
        print(statement)
        if table_name in Base.metadata.tables:
            table = Base.metadata.tables[table_name]
            create_table_sql = str(table.compile(engine)).strip()
            print(sqlalchemy.text(create_table_sql))
            db.execute(sqlalchemy.text(create_table_sql))
            db.commit()
        statement = statement.strip()
        print(statement)
        if statement:
            db.execute(sqlalchemy.text(statement))
            db.commit()
                
                
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3660)