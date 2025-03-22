import warnings
warnings.filterwarnings("ignore")
import os
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, ForeignKey, DateTime, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from dotenv import load_dotenv
from sqlalchemy.sql import func

# Load environment variables
load_dotenv()

# Get the database URL from the environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    DATABASE_URL = "sqlite:///./wagah.db"
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
    its = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    passport_number = Column(String, unique=True, nullable=False)
    passport_expiry = Column(Date, nullable=False)
    visa_number = Column(String, unique=True, nullable=False)
    mode_of_transport = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    arrived = Column(Boolean, default=False, nullable=False)
    arrival_timestamp = Column(DateTime, nullable=True)
    departed = Column(Boolean, default=False, nullable=False)
    departure_timestamp = Column(DateTime, nullable=True)
    arrival_date = Column(Date, default=func.current_date(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    booking_info = relationship("BookingInfo", back_populates="master", uselist=False)
    processed_info = relationship("ProcessedMaster", back_populates="master", uselist=False)

# Define the Transport base model
class Transport(Base):
    __tablename__ = "transport"
    id = Column(Integer, primary_key=True, index=True)
    departure_time = Column(Time, nullable=True)
    type = Column(String, nullable=False)
    transport_type = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(String, default="active", nullable=False)

    __mapper_args__ = {
        'polymorphic_on': transport_type,
        'polymorphic_identity': 'transport'
    }

    schedules = relationship("Schedule", back_populates="transport")

# Define the Bus model
class Bus(Transport):
    __tablename__ = "bus"
    bus_id = Column(Integer, ForeignKey('transport.id'), primary_key=True)
    bus_number = Column(Integer, nullable=False, unique=True)
    no_of_seats = Column(Integer, nullable=False)
    bus_type = Column(String, index=True, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'bus',
    }

# Define the Plane model
class Plane(Transport):
    __tablename__ = "plane"
    plane_id = Column(Integer, ForeignKey('transport.id'), primary_key=True)
    company = Column(String, nullable=False)
    flight_number = Column(String, nullable=False, unique=True)

    __mapper_args__ = {
        'polymorphic_identity': 'plane',
    }

# Define the Train model
class Train(Transport):
    __tablename__ = "train"
    train_id = Column(Integer, ForeignKey('transport.id'), primary_key=True)
    train_name = Column(String, nullable=False)
    train_number = Column(String, nullable=False, unique=True)

    __mapper_args__ = {
        'polymorphic_identity': 'train',
    }

# Define the BookingInfo model
class BookingInfo(Base):
    __tablename__ = "booking_info"
    its = Column(Integer, ForeignKey('master.its'), primary_key=True, index=True)
    mode = Column(Integer, index=True, nullable=False)
    issued = Column(Boolean, default=False, nullable=False)
    departed = Column(Boolean, default=False, nullable=False)
    self_issued = Column(Boolean, default=False, nullable=False)
    seat_number = Column(String, nullable=True)
    transport_id = Column(Integer, ForeignKey('transport.id'), nullable=False)
    coach_number = Column(String, nullable=True)
    cabin_number = Column(String, nullable=True)
    status = Column(String, default='pending', nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    master = relationship("Master", back_populates="booking_info")
    transport = relationship("Transport")

# Define the Schedule model
class Schedule(Base):
    __tablename__ = 'schedules'
    id = Column(Integer, primary_key=True, index=True)
    transport_id = Column(Integer, ForeignKey('transport.id'), nullable=False)
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)
    route = Column(String, index=True, nullable=False)
    status = Column(String, default='scheduled', nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    transport = relationship("Transport", back_populates="schedules")

# Define the User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # admin, staff, or user
    designation = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    processed_masters = relationship("ProcessedMaster", back_populates="processed_by_user")

# Define the ProcessedMaster model
class ProcessedMaster(Base):
    __tablename__ = "processed_master"
    id = Column(Integer, primary_key=True, index=True)
    its = Column(Integer, ForeignKey('master.its'), unique=True, index=True, nullable=False)
    first_name = Column(String, index=True, nullable=False)
    middle_name = Column(String, index=True, nullable=True)
    last_name = Column(String, index=True, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    passport_number = Column(String, index=True, nullable=False)
    passport_expiry = Column(Date, index=True, nullable=False)
    visa_number = Column(String, index=True, nullable=False)
    mode_of_transport = Column(String, index=True, nullable=False)
    phone = Column(String, index=True, nullable=True)
    arrived = Column(Boolean, default=False, nullable=False)
    processed_timestamp = Column(DateTime, default=func.now(), nullable=False)
    processed_by_username = Column(String, ForeignKey('users.username'), nullable=False)

    master = relationship("Master", back_populates="processed_info")
    processed_by_user = relationship("User", back_populates="processed_masters")

# Create all tables in the database
Base.metadata.create_all(bind=engine)
