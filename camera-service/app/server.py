"""HTTP-интерфейс сервиса камер (протокол v1).

    GET  /health            состояние сервиса (без токена)
    GET  /v1/cameras        список камер
    GET  /v1/watchlist      текущий список разыскиваемых ГРЗ
    PUT  /v1/watchlist      заменить список: {"plates": ["А123ВК43", ...]}  (шлёт сервис ГИБДД)
    POST /v1/detections     ручная фиксация: {"plate": "А123ВК43", "camera_code": "CAM-08"}

Все маршруты /v1/* требуют заголовок X-Service-Token. Ошибки возвращаются как {"detail": "..."}.
"""
import hmac
import json
import logging
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from .cameras import Camera
from .config import Settings
from .emitter import Emitter, UnknownCamera
from .gibdd_client import DeliveryError, DeliveryRejected
from .watchlist import Watchlist

log = logging.getLogger("camera-service")

MAX_BODY_BYTES = 64 * 1024
MAX_PLATES = 5000
MAX_PLATE_LENGTH = 20


class CameraApp:
    """Состояние сервиса, которое видят обработчики запросов."""

    def __init__(self, settings: Settings, cameras, watchlist: Watchlist, emitter: Emitter):
        self.settings = settings
        self.cameras = cameras
        self.watchlist = watchlist
        self.emitter = emitter


class RequestError(Exception):
    def __init__(self, status: int, detail: str, extra: Optional[Dict[str, Any]] = None):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.extra = extra or {}


def make_server(app: CameraApp, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "CameraService/1.0"

        # --- вспомогательное -------------------------------------------------
        def _send(self, status: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _check_token(self) -> None:
            expected = app.settings.service_token
            if not expected:
                raise RequestError(503, "SERVICE_TOKEN не настроен на сервисе камер")
            given = self.headers.get("X-Service-Token") or ""
            if not hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
                raise RequestError(401, "Неверный токен сервиса")

        def _read_json(self) -> Dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise RequestError(400, "Некорректный заголовок Content-Length")
            if length > MAX_BODY_BYTES:
                raise RequestError(413, f"Тело запроса больше {MAX_BODY_BYTES} байт")
            raw = self.rfile.read(length) if length else b""
            try:
                data = json.loads(raw.decode("utf-8") or "null")
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise RequestError(400, "Тело запроса не является корректным JSON")
            if not isinstance(data, dict):
                raise RequestError(400, "Ожидается JSON-объект")
            return data

        def _dispatch(self, method: str) -> None:
            try:
                path = self.path.split("?", 1)[0].rstrip("/") or "/"
                routes = {
                    ("GET", "/health"): (False, self._health),
                    ("GET", "/v1/cameras"): (True, self._cameras),
                    ("GET", "/v1/watchlist"): (True, self._get_watchlist),
                    ("PUT", "/v1/watchlist"): (True, self._put_watchlist),
                    ("POST", "/v1/detections"): (True, self._detect),
                }
                entry = routes.get((method, path))
                if entry is None:
                    known = {p for (_, p) in routes}
                    if path in known:
                        raise RequestError(405, f"Метод {method} не поддерживается для {path}")
                    raise RequestError(404, "Not Found")
                needs_token, handler = entry
                if needs_token:
                    self._check_token()
                status, payload = handler()
                self._send(status, payload)
            except RequestError as error:
                self._send(error.status, {"detail": error.detail, **error.extra})
            except Exception:
                log.exception("Необработанная ошибка в %s %s", method, self.path)
                self._send(500, {"detail": "Внутренняя ошибка сервиса камер"})

        def do_GET(self):
            self._dispatch("GET")

        def do_PUT(self):
            self._dispatch("PUT")

        def do_POST(self):
            self._dispatch("POST")

        def do_DELETE(self):
            self._dispatch("DELETE")

        def log_message(self, fmt, *args):  # стандартный вывод в stderr заменяем журналом
            log.debug("%s - %s", self.address_string(), fmt % args)

        # --- маршруты ----------------------------------------------------------
        def _health(self):
            return 200, {"status": "ok", "cameras": len(app.cameras), "watchlist": len(app.watchlist)}

        def _cameras(self):
            return 200, {"cameras": [asdict(c) for c in app.cameras]}

        def _get_watchlist(self):
            plates = app.watchlist.snapshot()
            return 200, {"plates": plates, "count": len(plates)}

        def _put_watchlist(self):
            data = self._read_json()
            plates = data.get("plates")
            if not isinstance(plates, list):
                raise RequestError(400, 'Ожидается {"plates": [список строк]}')
            if len(plates) > MAX_PLATES:
                raise RequestError(400, f"В списке не больше {MAX_PLATES} ГРЗ")
            for plate in plates:
                if not isinstance(plate, str) or not plate.strip() or len("".join(plate.split())) > MAX_PLATE_LENGTH:
                    raise RequestError(400, f"Недопустимый ГРЗ в списке: {plate!r}")
            count = app.watchlist.replace(plates)
            log.info("Получен список розыска: %s ГРЗ", count)
            return 200, {"count": count}

        def _detect(self):
            if not app.settings.manual_detections_enabled:
                raise RequestError(404, "Ручная фиксация отключена (ENABLE_MANUAL_DETECTIONS=false)")
            data = self._read_json()
            plate = data.get("plate")
            camera_code: Optional[str] = data.get("camera_code")
            if not isinstance(plate, str) or not plate.strip():
                raise RequestError(400, 'Нужно поле "plate" (ГРЗ)')
            if camera_code is not None and not isinstance(camera_code, str):
                raise RequestError(400, 'Поле "camera_code" должно быть строкой')
            try:
                return 200, app.emitter.detect(plate, camera_code)
            except UnknownCamera as error:
                raise RequestError(422, f"Неизвестная или отключённая камера: {error.code}")
            except DeliveryRejected as error:
                raise RequestError(
                    502,
                    f"Сервис ГИБДД отклонил событие: {error.detail}",
                    extra={"gibdd_status": error.status},
                )
            except DeliveryError as error:
                raise RequestError(502, f"Сервис ГИБДД недоступен: {error}")

    return ThreadingHTTPServer((host, port), Handler)
