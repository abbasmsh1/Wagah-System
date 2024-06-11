import os
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from dotenv import load_dotenv
from sqlalchemy.sql import func
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
    DOB = Column(Date)
    passport_No = Column(String, unique=True, index=True)
    passport_Expiry = Column(Date, index=True)
    Visa_No = Column(String, index=True)
    Mode_of_Transport = Column(String, index=True)
    phone = Column(String, index=True)
    arrived = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=func.now())

# Define the Group model with a composite primary key
# Define the Group model with a composite primary key
class Group(Base):
    __tablename__ = "group"
    ID = Column(Integer, primary_key=True, index=True)
    leader_ITS = Column(Integer, ForeignKey('master.ITS'), index=True)
    leader = relationship("Master", foreign_keys=[leader_ITS])
    members = relationship("Master", secondary="group_info")

# Define the GroupInfo model with a composite primary key
class GroupInfo(Base):
    __tablename__ = "group_info"
    ID = Column(Integer, primary_key=True, index=True)
    group_ID = Column(Integer, ForeignKey('group.ID'), index=True)
    ITS = Column(Integer, ForeignKey('master.ITS'), index=True)

# Define the Booking_Info model with a composite primary key
from typing import Optional

class BookingInfo(Base):
    __tablename__ = "booking_info"
    Mode = Column(Integer, primary_key=True, index=True)
    ITS = Column(Integer, ForeignKey('master.ITS'), primary_key=True, index=True)
    Issued = Column(Boolean)
    Departed = Column(Boolean)
    Self_Issued = Column(Boolean, default=False)
    seat_number = Column(Integer)  # Add seat number column
    bus_number = Column(Integer)  # Add bus number column

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

class Transport(Base):
    __tablename__ = "transport"
    id = Column(Integer, primary_key=True, index=True)
    departure_time = Column(Date, nullable=True)
    type = Column(String, nullable=False)
    transport_type = Column(String, nullable=False)

    __mapper_args__ = {
        'polymorphic_on': transport_type,
        'polymorphic_identity': 'transport'
    }

class Bus(Transport):
    __tablename__ = "bus"
    bus_id = Column(Integer, ForeignKey('transport.id'), primary_key=True)
    bus_number = Column(Integer, nullable=False)
    no_of_seats = Column(Integer, nullable=False)
    type = Column(String, index=True,nullable=True)
    __mapper_args__ = {
        'polymorphic_identity': 'bus',
    }

class Train(Transport):
    __tablename__ = "train"
    train_id = Column(Integer, ForeignKey('transport.id'), primary_key=True)
    company = Column(String, nullable=True)

    __mapper_args__ = {
        'polymorphic_identity': 'train',
    }

class Plane(Transport):
    __tablename__ = "plane"
    plane_id = Column(Integer, ForeignKey('transport.id'), primary_key=True)
    company = Column(String, nullable=True)
    type = Column(String, index=True)

    __mapper_args__ = {
        'polymorphic_identity': 'plane',
    }

class Shuttle(Transport):
    __tablename__ = "shuttle"
    shuttle_id = Column(Integer, ForeignKey('transport.id'), primary_key=True)
    destination = Column(String, nullable=False)
    no_of_seats = Column(Integer, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'shuttle',
    }

class Schedule(Base):
    __tablename__ = 'schedules'
    id = Column(Integer, primary_key=True, index=True)
    transport_id = Column(Integer, ForeignKey('transport.id'))
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    route = Column(String, index=True)
    transport = relationship("Transport")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    designation = Column(String)
    
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

