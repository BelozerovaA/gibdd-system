from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import WantedVehicle, Vehicle, Employee, ViolationCategory
from ..schemas import WantedVehicleCreate, WantedVehicleResponse
from ..auth import get_current_user

router = APIRouter()


@router.get("/my", response_model=List[WantedVehicleResponse])
def get_my_wanted(
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    vehicles = db.query(WantedVehicle).filter(
        WantedVehicle.employee_id == current_user.id,
        WantedVehicle.is_active == True
    ).all()

    result = []
    for wv in vehicles:
        v = db.query(Vehicle).filter(Vehicle.id == wv.vehicle_id).first()
        result.append(WantedVehicleResponse(
            id=wv.id,
            plate=v.plate if v else "-",
            model=v.model if v else "-",
            color=v.color if v else "-",
            status=wv.status,
            fix_time=wv.fix_time or "-",
            fix_date=wv.fix_date or "-",
            fix_address=wv.fix_address or "-",
            employee_name=current_user.full_name,
            reaction_status=wv.reaction_status or "Ожидает",
            found_status=wv.found_status or "Нет"
        ))
    return result


@router.get("/all", response_model=List[WantedVehicleResponse])
def get_all_wanted(
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    vehicles = db.query(WantedVehicle).filter(
        WantedVehicle.is_active == True
    ).all()

    result = []
    for wv in vehicles:
        v = db.query(Vehicle).filter(Vehicle.id == wv.vehicle_id).first()
        emp = db.query(Employee).filter(Employee.id == wv.employee_id).first()
        result.append(WantedVehicleResponse(
            id=wv.id,
            plate=v.plate if v else "-",
            model=v.model if v else "-",
            color=v.color if v else "-",
            status=wv.status,
            fix_time=wv.fix_time or "-",
            fix_date=wv.fix_date or "-",
            fix_address=wv.fix_address or "-",
            employee_name=emp.full_name if emp else "-",
            reaction_status=wv.reaction_status or "Ожидает",
            found_status=wv.found_status or "Нет"
        ))
    return result


@router.post("/add")
def add_wanted(
        data: WantedVehicleCreate,
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.plate == data.plate).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    existing = db.query(WantedVehicle).filter(
        WantedVehicle.vehicle_id == vehicle.id,
        WantedVehicle.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Автомобиль уже в розыске")

    category = db.query(ViolationCategory).filter(
        ViolationCategory.name == data.reason
    ).first()

    if not category:
        category = ViolationCategory(
            code="CUSTOM",
            name=data.reason,
            description=f"Причина: {data.reason}"
        )
        db.add(category)
        db.commit()
        db.refresh(category)

    wanted = WantedVehicle(
        vehicle_id=vehicle.id,
        employee_id=current_user.id,
        violation_category_id=category.id,
        reason=data.reason,
        wanted_date=datetime.now().strftime("%d.%m.%Y"),
        status="В розыске",
        is_active=True,
        reaction_status="Ожидает",
        found_status="Нет"
    )

    db.add(wanted)
    db.commit()
    db.refresh(wanted)

    return {"message": f"Автомобиль {data.plate} добавлен в розыск", "id": wanted.id}


@router.post("/take/{wanted_id}")
def take_wanted(
        wanted_id: int,
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Передать розыск автомобиля текущему сотруднику.

    Запись прежнего сотрудника закрывается (статус «Передан»), для текущего
    создаётся новая. Так по одному автомобилю всегда одна активная запись.
    """
    wanted = db.query(WantedVehicle).filter(
        WantedVehicle.id == wanted_id,
        WantedVehicle.is_active == True
    ).first()

    if not wanted:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if wanted.employee_id == current_user.id:
        raise HTTPException(status_code=400, detail="Это уже ваш розыск")

    if wanted.status != "В розыске":
        raise HTTPException(status_code=400, detail="Автомобиль уже не находится в розыске")

    new_wanted = WantedVehicle(
        vehicle_id=wanted.vehicle_id,
        employee_id=current_user.id,
        violation_category_id=wanted.violation_category_id,
        reason=wanted.reason,
        wanted_date=datetime.now().strftime("%d.%m.%Y"),
        status="В розыске",
        is_active=True,
        fix_date=wanted.fix_date,
        fix_time=wanted.fix_time,
        fix_address=wanted.fix_address,
        fix_camera_id=wanted.fix_camera_id,
        reaction_status="Ожидает",
        found_status="Нет"
    )

    wanted.is_active = False
    wanted.status = "Передан"

    db.add(new_wanted)
    db.commit()
    db.refresh(new_wanted)

    vehicle = db.query(Vehicle).filter(Vehicle.id == wanted.vehicle_id).first()

    return {
        "message": f"Автомобиль {vehicle.plate if vehicle else ''} взят в розыск",
        "id": new_wanted.id
    }


@router.delete("/{plate}")
def delete_wanted(
        plate: str,
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.plate == plate).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    wanted = db.query(WantedVehicle).filter(
        WantedVehicle.vehicle_id == vehicle.id,
        WantedVehicle.employee_id == current_user.id,
        WantedVehicle.is_active == True
    ).first()

    if not wanted:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    wanted.is_active = False
    wanted.status = "Удален"
    db.commit()

    return {"message": f"Автомобиль {plate} удален из розыска"}


@router.get("/available-plates")
def get_available_plates(db: Session = Depends(get_db)):
    plates = db.query(Vehicle.plate).filter(
        ~Vehicle.id.in_(
            db.query(WantedVehicle.vehicle_id).filter(WantedVehicle.is_active == True)
        )
    ).all()
    return [p[0] for p in plates]


@router.get("/violation-categories")
def get_violation_categories(db: Session = Depends(get_db)):
    categories = db.query(ViolationCategory.name).all()
    return [c[0] for c in categories] if categories else ["Угон", "Попытка угона", "Нарушение ПДД"]