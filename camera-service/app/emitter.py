"""Имитация работы камер: время от времени «увидеть» автомобиль из списка розыска.

Реальной системы распознавания номеров нет, поэтому событие создаётся случайным выбором:
берётся случайный ГРЗ из списка, который прислал сервис ГИБДД, и случайная работающая камера.
Для сервиса ГИБДД это неотличимо от настоящей фиксации: он видит только событие по протоколу.
"""
import logging
import random
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .cameras import Camera, find_camera
from .gibdd_client import DeliveryError, GibddClient
from .watchlist import Watchlist, normalize_plate

log = logging.getLogger("camera-service")


class UnknownCamera(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def build_event(plate: str, camera: Camera, now: Optional[datetime] = None) -> Dict[str, Any]:
    moment = now or datetime.now(timezone.utc)
    return {
        "event_id": uuid.uuid4().hex,
        "plate": plate,
        "camera_code": camera.code,
        "detected_at": moment.isoformat(),
    }


class Emitter:
    def __init__(
        self,
        cameras: List[Camera],
        watchlist: Watchlist,
        client: GibddClient,
        interval: float,
        rng: Optional[random.Random] = None,
    ):
        self.cameras = cameras
        self.watchlist = watchlist
        self.client = client
        self.interval = interval
        self.rng = rng or random.Random()

    def tick(self) -> Optional[Dict[str, Any]]:
        """Один шаг: выбрать автомобиль и камеру и отправить событие. None, если отправлять нечего."""
        plates = self.watchlist.snapshot()
        active = [c for c in self.cameras if c.active]
        if not plates or not active:
            return None

        plate = self.rng.choice(plates)
        camera = self.rng.choice(active)
        event = build_event(plate, camera)
        try:
            result = self.client.send_detection(event)
        except DeliveryError as error:
            log.warning("Событие %s (%s, %s) не доставлено: %s", event["event_id"], plate, camera.code, error)
            return None
        log.info("Зафиксирован %s на %s: ответ ГИБДД %s", plate, camera.code, result)
        return result

    def detect(self, plate: str, camera_code: Optional[str] = None) -> Dict[str, Any]:
        """Ручная фиксация (для демонстрации и проверки): отправить событие немедленно.

        Выбрасывает UnknownCamera, если код камеры не найден, и DeliveryError, если сервис
        ГИБДД недоступен или отклонил событие.
        """
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
        result = self.client.send_detection(event)
        return {"event": event, "gibdd_response": result}

    def run(self, stop: threading.Event) -> None:
        """Цикл работы: ждать interval секунд, сделать шаг, повторять до остановки."""
        log.info("Камеры включены, интервал фиксации %s с", self.interval)
        while not stop.wait(self.interval):
            try:
                self.tick()
            except Exception:  # сбой одного шага не должен остановить камеры
                log.exception("Ошибка при фиксации")
