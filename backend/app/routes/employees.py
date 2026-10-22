from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import Employee
from ..schemas import UserResponse
from ..auth import get_current_user

router = APIRouter()


class ProfileUpdate(BaseModel):
    email: Optional[str] = Field(None, max_length=120)
    phone: Optional[str] = Field(None, max_length=40)


def _to_response(emp: Employee) -> UserResponse:
    return UserResponse(
        id=emp.id,
        login=emp.login,
        full_name=emp.full_name,
        birth_date=emp.birth_date,
        phone=emp.phone,
        email=emp.email,
        position=emp.position,
        hire_date=emp.hire_date,
        department_name=emp.department.name if emp.department else None,
        is_active=bool(emp.is_active),
    )


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: Employee = Depends(get_current_user),
):
    return _to_response(current_user)


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    data: ProfileUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emp = db.query(Employee).filter(Employee.id == current_user.id).first()
    if data.email is not None:
        emp.email = data.email.strip() or None
    if data.phone is not None:
        emp.phone = data.phone.strip() or None
    db.commit()
    db.refresh(emp)
    return _to_response(emp)


@router.get("/", response_model=List[UserResponse])
def get_employees(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employees = db.query(Employee).filter(Employee.is_active == True).all()
    return [_to_response(e) for e in employees]
