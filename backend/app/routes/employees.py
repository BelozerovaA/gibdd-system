from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Employee
from ..schemas import UserResponse
from ..auth import get_current_user

router = APIRouter()


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


@router.get("/", response_model=List[UserResponse])
def get_employees(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employees = db.query(Employee).filter(Employee.is_active == True).all()
    return [_to_response(e) for e in employees]
