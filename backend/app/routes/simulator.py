import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Employee
from ..auth import get_current_user
from ..services.simulator import simulator_manager
from ..services.email import EmailNotifier
from ..websocket.manager import manager
from .. import runtime

router = APIRouter()
email_notifier = EmailNotifier()


def _on_detected(employee_id: int, employee_email: str):
    def _callback(payload: dict):
        message = {"type": "detection", **payload}

        if runtime.main_loop:
            asyncio.run_coroutine_threadsafe(
                manager.send_personal_message(employee_id, message),
                runtime.main_loop,
            )

        if employee_email:
            email_notifier.send_alert_async(
                employee_email,
                payload["plate"],
                payload["address"],
                payload["time"],
                payload["date"],
            )

    return _callback


@router.post("/start")
def start_simulator(
    current_user: Employee = Depends(get_current_user),
):
    simulator_manager.start(
        current_user.id,
        _on_detected(current_user.id, current_user.email),
    )
    return {"message": "Симулятор запущен", "running": True}


@router.post("/stop")
def stop_simulator(
    current_user: Employee = Depends(get_current_user),
):
    simulator_manager.stop(current_user.id)
    return {"message": "Симулятор остановлен", "running": False}


@router.get("/status")
def simulator_status(
    current_user: Employee = Depends(get_current_user),
):
    return {"running": simulator_manager.status(current_user.id)}


@router.post("/resume")
def resume_simulator(
    current_user: Employee = Depends(get_current_user),
):
    """Вызывается фронтом после того, как пользователь отреагировал на оповещение
    (нажал «Принято» и, через минуту, ответил на вопрос «Автомобиль найден?»)."""
    simulator_manager.resume_after_reaction(current_user.id)
    return {"message": "OK"}
