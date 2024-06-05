import os
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the database URL from the environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

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
    first_name = Column(String, index=True)
    middle_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    DOB = Column(Date)
    passport_No = Column(String, unique=True, index=True)
    passport_Issue = Column(Date, index=True)
    passport_Expiry = Column(Date, index=True)
    Visa_No = Column(String, index=True)
    Mode_of_Transport = Column(String, index=True)

# Define the Group model with a composite primary key
class Group(Base):
    __tablename__ = "group"
    ID = Column(Integer, primary_key=True, index=True)
    ITS = Column(Integer, ForeignKey('master.ITS'), primary_key=True, index=True)
    no_Members = Column(Integer, index=True)

# Define the Group_Info model with a composite primary key
class GroupInfo(Base):
    __tablename__ = "group_info"
    ID = Column(Integer, primary_key=True, index=True)
    ITS = Column(Integer, ForeignKey('master.ITS'), primary_key=True, index=True)

# Define the Booking_Info model with a composite primary key
class BookingInfo(Base):
    __tablename__ = "booking_info"
    Mode = Column(Integer, primary_key=True, index=True)
    ITS = Column(Integer, ForeignKey('master.ITS'), primary_key=True, index=True)
    Issued = Column(Boolean)
    Departed = Column(Boolean)
    Self_Issued = Column(Boolean)

class Transport(Base):
    __tablename__ = "Transport"
    id = Column(Integer, primary_key=True, index=True)
    departure_time = Column(Date, nullable=False)
    type = Column(String, nullable=False)
    transport_type = Column(String, nullable=False)

    __mapper_args__ = {
        'polymorphic_on': transport_type,
        'polymorphic_identity': 'transport'
    }

class Bus(Transport):
    __tablename__ = "Bus"
    bus_id = Column(Integer, ForeignKey('Transport.id'), primary_key=True)
    bus_number = Column(String, nullable=False)
    no_of_seats = Column(Integer, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'bus',
    }

class Train(Transport):
    __tablename__ = "Train"
    train_id = Column(Integer, ForeignKey('Transport.id'), primary_key=True)
    company = Column(String, nullable=True)

    __mapper_args__ = {
        'polymorphic_identity': 'train',
    }

class Plane(Transport):
    __tablename__ = "Plane"
    plane_id = Column(Integer, ForeignKey('Transport.id'), primary_key=True)
    company = Column(String, nullable=True)

    __mapper_args__ = {
        'polymorphic_identity': 'plane',
    }

class Shuttle(Transport):
    __tablename__ = "Shuttle"
    shuttle_id = Column(Integer, ForeignKey('Transport.id'), primary_key=True)
    destination = Column(String, nullable=False)
    no_of_seats = Column(Integer, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'shuttle',
    }
# Create all tables in the database
Base.metadata.create_all(bind=engine)
