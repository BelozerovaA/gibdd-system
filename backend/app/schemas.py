from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    login: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    full_name: str
    position: str
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    login: str
    full_name: str
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[str] = None
    department_name: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

class VehicleCreate(BaseModel):
    plate: str
    model: Optional[str] = None
    color: Optional[str] = None
    vin: Optional[str] = None
    owner_name: Optional[str] = None
    category: Optional[str] = None

class VehicleResponse(BaseModel):
    id: int
    plate: str
    model: Optional[str] = None
    color: Optional[str] = None

    class Config:
        from_attributes = True

class WantedVehicleCreate(BaseModel):
    plate: str
    reason: str

class WantedVehicleResponse(BaseModel):
    id: int
    plate: str
    model: Optional[str] = None
    color: Optional[str] = None
    status: str
    fix_time: Optional[str] = "-"
    fix_date: Optional[str] = "-"
    fix_address: Optional[str] = "-"
    employee_name: Optional[str] = None
    reaction_status: Optional[str] = "Ожидает"
    found_status: Optional[str] = "Нет"

class CameraResponse(BaseModel):
    id: int
    camera_id: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    camera_type: Optional[str] = None
    speed_limit: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    id: int
    vehicle_plate: str
    alert_date: str
    alert_time: str
    address: str
    camera_id: Optional[int] = None
    reaction_status: Optional[str] = "Ожидает"
    found_status: Optional[str] = "Нет"
    wanted_status: Optional[str] = "В розыске"
    is_viewed: bool

class AlertReactionRequest(BaseModel):
    reaction_status: str

class AlertFoundRequest(BaseModel):
    found_status: str