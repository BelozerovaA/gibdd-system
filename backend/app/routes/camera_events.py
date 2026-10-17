from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from ..schemas import CameraEvent
from ..service_auth import require_service_token
from ..services.detections import (
    UnknownCameraError,
    mark_notification_sent,
    process_camera_event,
)
from ..services.email import EmailNotifier
from ..websocket.manager import manager

router = APIRouter()

email_notifier = EmailNotifier()


@router.post("/camera-events", dependencies=[Depends(require_service_token)])
async def receive_camera_event(event: CameraEvent):
    """Принимает от сервиса камер событие «камера зафиксировала автомобиль».

    Если автомобиль в розыске, создаёт оповещение, отправляет его сотруднику по WebSocket
    и (при настроенной почте) письмом. Ответ всегда сообщает, что произошло:
    {"status": "accepted", "alert_id": ..., "delivered": ...} или
    {"status": "ignored", "reason": "not_wanted" | "pending_alert" | "cooldown" | "duplicate"}.
    """
    try:
        # работа с БД синхронная, поэтому выполняется в пуле потоков, а не в event loop
        outcome = await run_in_threadpool(
            process_camera_event,
            event.event_id,
            event.plate,
            event.camera_code,
            event.detected_at,
        )
    except UnknownCameraError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Неизвестная или отключённая камера: {error.camera_code}",
        )

    if outcome.status != "accepted":
        return {"status": "ignored", "reason": outcome.reason}

    delivered = await manager.send_personal_message(
        outcome.employee_id,
        {"type": "detection", **outcome.payload},
    )
    if delivered:
        await run_in_threadpool(mark_notification_sent, outcome.alert_id)

    if outcome.employee_email:
        email_notifier.send_alert_async(
            outcome.employee_email,
            outcome.payload["plate"],
            outcome.payload["address"],
            outcome.payload["time"],
            outcome.payload["date"],
        )

    return {"status": "accepted", "alert_id": outcome.alert_id, "delivered": delivered}
