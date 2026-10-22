"""Рассылка списка разыскиваемых ГРЗ подключённым камерам по WebSocket."""
from __future__ import annotations

import asyncio
import os
from threading import Event, Thread
from typing import Callable, List, Optional

DEFAULT_RESYNC_SECONDS = 30
DEFAULT_RETRY_SECONDS = 5


def load_active_plates() -> List[str]:
    from ..database import SessionLocal
    from ..models import Vehicle, WantedVehicle

    with SessionLocal() as db:
        rows = (
            db.query(Vehicle.plate)
            .join(WantedVehicle, WantedVehicle.vehicle_id == Vehicle.id)
            .filter(WantedVehicle.is_active == True, WantedVehicle.status == "В розыске")  # noqa: E712
            .distinct()
            .all()
        )
    return sorted(row[0] for row in rows)


class WatchlistPublisher:
    def __init__(self, plates_provider: Callable[[], List[str]] = load_active_plates):
        self._plates_provider = plates_provider
        self._wake = Event()
        self._stop = Event()
        self._thread: Optional[Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._resync_seconds = DEFAULT_RESYNC_SECONDS
        self._retry_seconds = DEFAULT_RETRY_SECONDS
        self._last_ok: Optional[bool] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def start(self, resync_seconds: float = DEFAULT_RESYNC_SECONDS,
              retry_seconds: float = DEFAULT_RETRY_SECONDS) -> None:
        if self.running:
            return
        self._resync_seconds = resync_seconds
        self._retry_seconds = min(retry_seconds, resync_seconds)
        self._stop.clear()
        self._wake.clear()
        self._thread = Thread(target=self._run, name="watchlist-publisher", daemon=True)
        self._thread.start()

    def start_from_env(self) -> None:
        self.start(
            resync_seconds=int(os.getenv("WATCHLIST_RESYNC_SECONDS", str(DEFAULT_RESYNC_SECONDS))),
        )

    def kick(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def publish_once(self) -> bool:
        from ..websocket.camera_manager import camera_manager

        try:
            plates = self._plates_provider()
        except Exception as error:
            print(f"Ошибка при подготовке списка розыска: {error}")
            self._last_ok = False
            return False

        message = {"type": "watchlist", "plates": plates}
        loop = self._loop
        if loop is None or not loop.is_running():
            if self._last_ok is not False:
                print("Event loop недоступен: список розыска камерам не отправлен")
            self._last_ok = False
            return False

        try:
            future = asyncio.run_coroutine_threadsafe(camera_manager.broadcast(message), loop)
            sent = future.result(timeout=5)
        except Exception as error:
            if self._last_ok is not False:
                print(f"Не удалось разослать список розыска камерам: {error}")
            self._last_ok = False
            return False

        ok = True
        if ok and self._last_ok is False:
            print(f"Список розыска разослан камерам ({sent} соединений)")
        self._last_ok = ok
        return ok

    async def send_to_camera(self, camera_code: str) -> bool:
        from ..websocket.camera_manager import camera_manager

        try:
            plates = self._plates_provider()
        except Exception as error:
            print(f"Ошибка при подготовке списка розыска: {error}")
            return False
        return await camera_manager.send_to(camera_code, {"type": "watchlist", "plates": plates})

    def _run(self) -> None:
        while not self._stop.is_set():
            ok = self.publish_once()
            self._wake.wait(timeout=self._resync_seconds if ok else self._retry_seconds)
            self._wake.clear()


watchlist_publisher = WatchlistPublisher()
