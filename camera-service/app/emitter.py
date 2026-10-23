from __future__ import annotations

import logging
import random
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cameras import Camera, find_camera
from .watchlist import Watchlist, normalize_plate
from .ws_client import CameraHub, DeliveryError

log = logging.getLogger("camera-service")


class UnknownCamera(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def build_event(plate: str, camera: Camera) -> Dict[str, Any]:
    moment = datetime.now(timezone.utc)
    return {
        "event_id": uuid.uuid4().hex,
        "plate": plate,
        "camera_code": camera.code,
        "detected_at": moment.isoformat(),
    }


class Emitter:
    def __init__(self, cameras, watchlist, hub, interval, rng=None):
        self.cameras = cameras
        self.watchlist = watchlist
        self.hub = hub
        self.interval = interval
        self.rng = rng or random.Random()

    def tick(self):
        plates = self.watchlist.snapshot()
        active = [c for c in self.cameras if c.active]
        if not plates or not active:
            return None
        plate = self.rng.choice(plates)
        camera = self.rng.choice(active)
        event = build_event(plate, camera)
        sock = self.hub.get(camera.code)
        if sock is None:
            log.warning("Нет WS-клиента для камеры %s", camera.code)
            return None
        try:
            result = sock.send_detection(event)
        except DeliveryError as error:
            log.warning("Событие %s (%s, %s) не доставлено: %s", event["event_id"], plate, camera.code, error)
            return None
        log.info("Зафиксирован %s на %s: ответ ГИБДД %s", plate, camera.code, result)
        return result

    def detect(self, plate: str, camera_code: Optional[str] = None):
        if camera_code is None:
            active = [c for c in self.cameras if c.active]
            if not active:
                raise UnknownCamera("(нет работающих камер)")
            camera = self.rng.choice(active)
        else:
            camera = find_camera(self.cameras, camera_code)
            if camera is None or not camera.active:
                raise UnknownCamera(camera_code)
        event = build_event(normalize_plate(plate), camera)
        sock = self.hub.get(camera.code)
        if sock is None:
            raise DeliveryError(f"нет WS-клиента для {camera.code}")
        result = sock.send_detection(event)
        return {"event": event, "gibdd_response": result}

    def run(self, stop: threading.Event) -> None:
        log.info("Камеры включены, интервал фиксации %s с (транспорт: WebSocket)", self.interval)
        while not stop.wait(self.interval):
            try:
                self.tick()
            except Exception:
                log.exception("Ошибка при фиксации")