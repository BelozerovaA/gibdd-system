from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Alert, Employee, WantedVehicle
from ..schemas import AlertFoundRequest, AlertReactionRequest, AlertResponse

router = APIRouter()

DATE_FORMAT = "%d.%m.%Y"
HISTORY_LIMIT = 200


def in_period(alert_date: str, period: Optional[str], now: datetime) -> bool:
    """Попадает ли дата оповещения («дд.мм.гггг») в выбранный период.

    Даты в БД хранятся строками, поэтому сравнивать их как строки нельзя
    («05.09.2026» > «03.10.2026»). Переводим в настоящие даты.
    """
    if period not in ("today", "week", "month"):
        return True  # период не задан или неизвестен: фильтр не применяется

    try:
        alert_day = datetime.strptime(alert_date, DATE_FORMAT).date()
    except (TypeError, ValueError):
        return False

    today = now.date()
    if period == "today":
        start = today
    elif period == "week":
        start = today - timedelta(days=7)
    else:  # month
        start = today - timedelta(days=30)
    return alert_day >= start


def _get_own_alert(db: Session, alert_id: int, user: Employee) -> Alert:
    """Оповещение можно менять только тому сотруднику, которому оно адресовано."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.employee_id == user.id
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Оповещение не найдено")
    return alert


@router.get("/history", response_model=List[AlertResponse])
def get_alerts_history(
        period: Optional[str] = Query(None, description="today, week, month"),
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    alerts = db.query(Alert).filter(
        Alert.employee_id == current_user.id
    ).order_by(Alert.id.desc()).all()

    now = datetime.now()
    alerts = [a for a in alerts if in_period(a.alert_date, period, now)][:HISTORY_LIMIT]

    result = []
    for alert in alerts:
        wanted = db.query(WantedVehicle).filter(WantedVehicle.id == alert.wanted_id).first()
        result.append(AlertResponse(
            id=alert.id,
            vehicle_plate=alert.vehicle_plate,
            alert_date=alert.alert_date,
            alert_time=alert.alert_time,
            address=alert.address,
            camera_id=alert.camera_id,
            reaction_status=alert.reaction_status or "Ожидает",
            found_status=alert.found_status or "Нет",
            wanted_status=wanted.status if wanted else "В розыске",
            is_viewed=alert.is_viewed
        ))

    return result


@router.put("/{alert_id}/reaction")
def update_alert_reaction(
        alert_id: int,
        data: AlertReactionRequest,
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    alert = _get_own_alert(db, alert_id, current_user)

    alert.reaction_status = data.reaction_status
    alert.is_viewed = True

    wanted = db.query(WantedVehicle).filter(WantedVehicle.id == alert.wanted_id).first()
    if wanted:
        wanted.reaction_status = data.reaction_status

    db.commit()
    return {"message": "Статус обновлен"}


@router.put("/{alert_id}/found")
def update_alert_found(
        alert_id: int,
        data: AlertFoundRequest,
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    alert = _get_own_alert(db, alert_id, current_user)

    alert.found_status = data.found_status

    wanted = db.query(WantedVehicle).filter(WantedVehicle.id == alert.wanted_id).first()
    if wanted:
        wanted.found_status = data.found_status
        if data.found_status == "Да":
            wanted.status = "Найден"
            wanted.reaction_status = "Принято"
        else:
            wanted.status = "В розыске"
            wanted.reaction_status = "Ожидает"

    db.commit()
    return {"message": "Статус найден обновлен"}


@router.get("/pending")
def get_pending_alerts(
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    alerts = db.query(Alert).filter(
        Alert.employee_id == current_user.id,
        Alert.found_status == "Нет",
        Alert.reaction_status == "Ожидает"
    ).order_by(Alert.id.desc()).limit(10).all()

    return [
        {
            "id": alert.id,
            "plate": alert.vehicle_plate,
            "address": alert.address,
            "date": alert.alert_date,
            "time": alert.alert_time
        }
        for alert in alerts
    ]
