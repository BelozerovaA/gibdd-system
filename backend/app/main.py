from contextlib import asynccontextmanager
import hmac
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from starlette.concurrency import run_in_threadpool

from . import models
from .auth import ALGORITHM, SECRET_KEY
from .database import engine
from .routes import alerts as alerts_routes
from .routes import auth as auth_routes
from .routes import cameras as cameras_routes
from .routes import employees as employees_routes
from .routes import vehicles as vehicles_routes
from .routes import wanted as wanted_routes
from .services.camera_client import watchlist_publisher
from .services.detections import (
    UnknownCameraError,
    mark_notification_sent,
    process_camera_event,
)
from .services.email import EmailNotifier
from .websocket.camera_manager import camera_manager
from .websocket.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    import asyncio
    watchlist_publisher.bind_loop(asyncio.get_running_loop())
    watchlist_publisher.start_from_env()
    yield
    watchlist_publisher.stop()


app = FastAPI(title="GIBDD API", version="1.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(employees_routes.router, prefix="/api/employees", tags=["employees"])
app.include_router(vehicles_routes.router, prefix="/api/vehicles", tags=["vehicles"])
app.include_router(wanted_routes.router, prefix="/api/wanted", tags=["wanted"])
app.include_router(alerts_routes.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(cameras_routes.router, prefix="/api/cameras", tags=["cameras"])

email_notifier = EmailNotifier()


@app.get("/")
def root():
    return {
        "message": "GIBDD API",
        "status": "running",
        "camera_ws": "/ws/cameras/{camera_code}?token=SERVICE_TOKEN",
        "cameras_connected": camera_manager.count(),
    }


def _employee_id_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") == "export":
            return None
        return payload.get("sub")
    except JWTError:
        return None


def _service_token_ok(token: str) -> bool:
    expected = os.getenv("SERVICE_TOKEN", "")
    if not expected or not token:
        return False
    return hmac.compare_digest(token.encode("utf-8"), expected.encode("utf-8"))


@app.websocket("/ws/{employee_id}")
async def websocket_endpoint(websocket: WebSocket, employee_id: int, token: str = ""):
    verified_id = _employee_id_from_token(token)
    if verified_id is None or int(verified_id) != employee_id:
        await websocket.close(code=4401)
        return

    await manager.connect(employee_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(employee_id, websocket)


@app.websocket("/ws/cameras/{camera_code}")
async def camera_websocket(websocket: WebSocket, camera_code: str, token: str = ""):
    """Одно WebSocket-соединение на камеру."""
    if not os.getenv("SERVICE_TOKEN", ""):
        await websocket.close(code=1013)
        return
    if not _service_token_ok(token):
        await websocket.close(code=4401)
        return

    code = (camera_code or "").strip()
    if not code:
        await websocket.close(code=1008)
        return

    await camera_manager.connect(code, websocket)
    await watchlist_publisher.send_to_camera(code)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "invalid_json"})
                continue

            msg_type = message.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if msg_type == "pong":
                continue
            if msg_type != "detection":
                await websocket.send_json({"type": "error", "detail": "unknown_type"})
                continue

            event_id = str(message.get("event_id") or "")
            plate = str(message.get("plate") or "")
            cam = code
            detected_at_raw = message.get("detected_at")

            if not event_id or not plate or not detected_at_raw:
                await websocket.send_json({
                    "type": "ack", "event_id": event_id, "status": "error", "detail": "missing_fields",
                })
                continue

            from datetime import datetime
            try:
                if isinstance(detected_at_raw, str):
                    detected_at = datetime.fromisoformat(detected_at_raw.replace("Z", "+00:00"))
                else:
                    raise ValueError("detected_at must be ISO string")
            except ValueError:
                await websocket.send_json({
                    "type": "ack", "event_id": event_id, "status": "error", "detail": "invalid_detected_at",
                })
                continue

            try:
                outcome = await run_in_threadpool(
                    process_camera_event, event_id, plate, cam, detected_at,
                )
            except UnknownCameraError as error:
                await websocket.send_json({
                    "type": "ack", "event_id": event_id, "status": "error",
                    "detail": f"unknown_camera:{error.camera_code}",
                })
                continue

            if outcome.status != "accepted":
                await websocket.send_json({
                    "type": "ack", "event_id": event_id, "status": "ignored", "reason": outcome.reason,
                })
                continue

            delivered = await manager.send_personal_message(
                outcome.employee_id, {"type": "detection", **outcome.payload},
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

            await websocket.send_json({
                "type": "ack", "event_id": event_id, "status": "accepted",
                "alert_id": outcome.alert_id, "delivered": delivered,
            })
    except WebSocketDisconnect:
        pass
    finally:
        await camera_manager.disconnect(code, websocket)
