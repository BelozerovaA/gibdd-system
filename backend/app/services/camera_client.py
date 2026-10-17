"""Отправка сервису камер списка разыскиваемых ГРЗ (ориентировки).

Сервис камер живёт отдельно (свой процесс и контейнер) и сам ничего не знает о розыске.
Поэтому сервис ГИБДД отправляет ему актуальный список по протоколу:

    PUT {CAMERA_SERVICE_URL}/v1/watchlist
    X-Service-Token: <SERVICE_TOKEN>
    {"plates": ["А123ВК43", "Е456КМ43"]}

Каждый раз отправляется полный список (снимок), а не отдельные изменения. Поэтому потерянная
отправка или перезапуск сервиса камер не приводят к рассинхронизации: следующая отправка
всё исправляет. Отправка идёт в фоновом потоке и не тормозит запросы пользователей.
"""
import json
import os
import urllib.error
import urllib.request
from threading import Event, Thread
from typing import Callable, List, Optional

DEFAULT_RESYNC_SECONDS = 30
DEFAULT_RETRY_SECONDS = 5  # после неудачной отправки повторяем чаще: сервис камер мог ещё не успеть запуститься
DEFAULT_TIMEOUT_SECONDS = 3.0


def build_request(base_url: str, token: str, plates: List[str]) -> urllib.request.Request:
    body = json.dumps({"plates": plates}, ensure_ascii=False).encode("utf-8")
    return urllib.request.Request(
        url=f"{base_url.rstrip('/')}/v1/watchlist",
        data=body,
        method="PUT",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Service-Token": token,
        },
    )


def load_active_plates() -> List[str]:
    """ГРЗ всех автомобилей, которые сейчас в розыске (без дублей, по алфавиту)."""
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
        self._base_url = ""
        self._token = ""
        self._resync_seconds = DEFAULT_RESYNC_SECONDS
        self._retry_seconds = DEFAULT_RETRY_SECONDS
        self._timeout = DEFAULT_TIMEOUT_SECONDS
        self._last_ok: Optional[bool] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, base_url: str, token: str, resync_seconds: float = DEFAULT_RESYNC_SECONDS,
              timeout: float = DEFAULT_TIMEOUT_SECONDS, retry_seconds: float = DEFAULT_RETRY_SECONDS) -> None:
        if self.running:
            return
        self._base_url, self._token = base_url, token
        self._resync_seconds, self._timeout = resync_seconds, timeout
        self._retry_seconds = min(retry_seconds, resync_seconds)
        self._stop.clear()
        self._wake.clear()
        self._thread = Thread(target=self._run, name="watchlist-publisher", daemon=True)
        self._thread.start()

    def start_from_env(self) -> None:
        """Запускает отправку, если в окружении указан адрес сервиса камер."""
        base_url = os.getenv("CAMERA_SERVICE_URL", "").strip()
        if not base_url:
            print("CAMERA_SERVICE_URL не задан: список розыска сервису камер не отправляется")
            return
        self.start(
            base_url=base_url,
            token=os.getenv("SERVICE_TOKEN", ""),
            resync_seconds=int(os.getenv("WATCHLIST_RESYNC_SECONDS", str(DEFAULT_RESYNC_SECONDS))),
        )

    def kick(self) -> None:
        """Список розыска изменился: отправить заново как можно скорее."""
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def publish_once(self) -> bool:
        """Одна отправка. True, если сервис камер принял список."""
        try:
            plates = self._plates_provider()
            request = build_request(self._base_url, self._token, plates)
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                ok = 200 <= response.status < 300
        except (urllib.error.URLError, OSError, ValueError) as error:
            ok = False
            if self._last_ok is not False:  # сообщаем об обрыве один раз, а не каждые 30 секунд
                print(f"Не удалось отправить список розыска сервису камер: {error}")
        except Exception as error:  # сбой чтения БД не должен убить поток
            ok = False
            print(f"Ошибка при подготовке списка розыска: {error}")
        if ok and self._last_ok is False:
            print("Связь с сервисом камер восстановлена, список розыска отправлен")
        self._last_ok = ok
        return ok

    def _run(self) -> None:
        while not self._stop.is_set():
            ok = self.publish_once()
            # если сервис камер недоступен, пробуем снова скоро, а не через полную паузу
            self._wake.wait(timeout=self._resync_seconds if ok else self._retry_seconds)
            self._wake.clear()


watchlist_publisher = WatchlistPublisher()
