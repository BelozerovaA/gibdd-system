"""Обработка события от сервиса камер: поиск розыска, создание оповещения в БД.

Правила (создавать ли оповещение) находятся в detection_rules.py, здесь только
запросы к базе и сохранение результата.
"""
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from ..database import SessionLocal
from ..models import Alert, Camera, Vehicle, WantedVehicle
from . import detection_rules as rules


class UnknownCameraError(Exception):
    """Камера с таким кодом не найдена в базе или отключена."""

    def __init__(self, camera_code: str):
        super().__init__(camera_code)
        self.camera_code = camera_code


@dataclass
class DetectionOutcome:
    status: str  # "accepted": оповещение создано, "ignored": событие принято, оповещения нет
    reason: Optional[str] = None
    alert_id: Optional[int] = None
    employee_id: Optional[int] = None
    employee_email: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


_deduplicator = rules.EventDeduplicator()


def _cooldown_seconds() -> int:
    try:
        return int(os.getenv("ALERT_COOLDOWN_SECONDS", "120"))
    except ValueError:
        return 120


def process_camera_event(
    event_id: str,
    plate: str,
    camera_code: str,
    detected_at: datetime,
) -> DetectionOutcome:
    """Создаёт оповещение, если автомобиль в розыске и сотрудника пора оповестить."""
    if _deduplicator.contains(event_id):
        return DetectionOutcome("ignored", rules.IGNORE_DUPLICATE)

    moment = rules.to_local_time(detected_at, os.getenv("APP_TIMEZONE", "Europe/Moscow"))
    plate = rules.normalize_plate(plate)

    with SessionLocal() as db:
        camera = (
            db.query(Camera)
            .filter(Camera.camera_id == camera_code, Camera.is_active == True)  # noqa: E712
            .first()
        )
        if camera is None:
            raise UnknownCameraError(camera_code)

        wanted = (
            db.query(WantedVehicle)
            .join(Vehicle, Vehicle.id == WantedVehicle.vehicle_id)
            .filter(
                Vehicle.plate == plate,
                WantedVehicle.is_active == True,  # noqa: E712
                WantedVehicle.status == "В розыске",
            )
            .first()
        )

        last_alert = None
        if wanted is not None:
            previous = (
                db.query(Alert)
                .filter(Alert.wanted_id == wanted.id)
                .order_by(Alert.id.desc())
                .first()
            )
            if previous is not None:
                last_alert = rules.LastAlert(
                    reaction_status=previous.reaction_status,
                    created_at=rules.parse_alert_moment(previous.alert_date, previous.alert_time),
                )

        reason = rules.decide(wanted is not None, last_alert, moment, _cooldown_seconds())
        if reason is not None:
            _deduplicator.add(event_id)
            return DetectionOutcome("ignored", reason)

        date_str, time_str = rules.format_alert_moment(moment)

        wanted.fix_date = date_str
        wanted.fix_time = time_str
        wanted.fix_address = camera.address
        wanted.fix_camera_id = str(camera.id)
        wanted.reaction_status = "Ожидает"

        alert = Alert(
            wanted_id=wanted.id,
            camera_id=camera.id,
            vehicle_plate=plate,
            alert_date=date_str,
            alert_time=time_str,
            address=camera.address,
            employee_id=wanted.employee_id,
            reaction_status="Ожидает",
            found_status="Нет",
            notification_sent=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        _deduplicator.add(event_id)

        employee = wanted.employee
        return DetectionOutcome(
            status="accepted",
            alert_id=alert.id,
            employee_id=wanted.employee_id,
            employee_email=employee.email if employee is not None else None,
            payload={
                "alert_id": alert.id,
                "wanted_id": wanted.id,
                "plate": plate,
                "camera_id": camera.id,
                "camera_number": rules.camera_number(camera.camera_id, camera.id),
                "address": camera.address,
                "latitude": camera.latitude,
                "longitude": camera.longitude,
                "date": date_str,
                "time": time_str,
            },
        )


def mark_notification_sent(alert_id: int) -> None:
    """Отмечает, что оповещение доставлено сотруднику по WebSocket."""
    with SessionLocal() as db:
        alert = db.get(Alert, alert_id)
        if alert is not None:
            alert.notification_sent = True
            db.commit()
