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
    def _callback(payload: dict) -> bool:
        message = {"type": "detection", **payload}
        delivered = False

        loop = runtime.main_loop
        if loop is not None and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                manager.send_personal_message(employee_id, message),
                loop,
            )
            try:
                delivered = bool(future.result(timeout=5))
            except Exception as error:
                print(f"Не удалось отправить оповещение по WebSocket: {error}")

        if employee_email:
            email_notifier.send_alert_async(
                employee_email,
                payload["plate"],
                payload["address"],
                payload["time"],
                payload["date"],
            )

        return delivered

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
    simulator_manager.resume_after_reaction(current_user.id)
    return {"message": "OK"}
