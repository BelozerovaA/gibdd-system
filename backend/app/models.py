from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    city = Column(String(100))
    address = Column(String(255))
    phone = Column(String(20))
    chief_name = Column(String(100))
    employees = relationship("Employee", back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    birth_date = Column(String(10))
    phone = Column(String(20))
    email = Column(String(100))
    position = Column(String(100))
    hire_date = Column(String(10))
    department_id = Column(Integer, ForeignKey("departments.id"))
    is_active = Column(Boolean, default=True)
    department = relationship("Department", back_populates="employees")
    wanted_vehicles = relationship("WantedVehicle", back_populates="employee")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate = Column(String(20), unique=True, nullable=False, index=True)
    model = Column(String(100))
    color = Column(String(20))
    vin = Column(String(50))
    owner_name = Column(String(100))
    category = Column(String(50))
    is_stolen = Column(Boolean, default=False)
    wanted = relationship("WantedVehicle", back_populates="vehicle", uselist=False)


class ViolationCategory(Base):
    __tablename__ = "violation_categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    fine_amount = Column(Integer)
    wanted_vehicles = relationship("WantedVehicle", back_populates="violation_category")


class WantedVehicle(Base):
    __tablename__ = "wanted_vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    violation_category_id = Column(Integer, ForeignKey("violation_categories.id"))
    reason = Column(String(255))
    wanted_date = Column(String(10))
    status = Column(String(50), default="В розыске")
    is_active = Column(Boolean, default=True)
    fix_date = Column(String(10))
    fix_time = Column(String(10))
    fix_address = Column(String(255))
    fix_camera_id = Column(String(10))
    reaction_status = Column(String(50), default="Ожидает")
    found_status = Column(String(10), default="Нет")
    vehicle = relationship("Vehicle", back_populates="wanted")
    employee = relationship("Employee", back_populates="wanted_vehicles")
    violation_category = relationship("ViolationCategory", back_populates="wanted_vehicles")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(20), unique=True, nullable=False)
    address = Column(String(255), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    camera_type = Column(String(50))
    speed_limit = Column(Integer)
    is_active = Column(Boolean, default=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    wanted_id = Column(Integer, ForeignKey("wanted_vehicles.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    vehicle_plate = Column(String(20), nullable=False)
    alert_date = Column(String(12), nullable=False)
    alert_time = Column(String(10), nullable=False)
    address = Column(String(255), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    is_viewed = Column(Boolean, default=False)
    reaction_status = Column(String(50), default="Ожидает")
    found_status = Column(String(10), default="Нет")
    notification_sent = Column(Boolean, default=False)


class UserLog(Base):
    __tablename__ = "user_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    action_type = Column(String(50), nullable=False)
    action_description = Column(String(255))
    action_date = Column(String(10), nullable=False)
    action_time = Column(String(10), nullable=False)