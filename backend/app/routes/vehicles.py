from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Vehicle, Employee
from ..auth import get_current_user

router = APIRouter()


@router.get("/")
def get_vehicles(
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    vehicles = db.query(Vehicle).all()
    return [{"plate": v.plate, "model": v.model} for v in vehicles]


@router.post("/")
def create_vehicle(
        plate: str,
        model: str,
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    existing = db.query(Vehicle).filter(Vehicle.plate == plate).first()
    if existing:
        raise HTTPException(status_code=400, detail="Автомобиль с таким ГРЗ уже существует")

    new_vehicle = Vehicle(plate=plate, model=model)
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return {"message": "Автомобиль добавлен", "id": new_vehicle.id}