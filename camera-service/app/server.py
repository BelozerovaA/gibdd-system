"""Локальный HTTP: health, камеры, ручная фиксация. Watchlist и detection — только WebSocket."""
import hmac
import json
import logging
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from .config import Settings
from .emitter import Emitter, UnknownCamera
from .watchlist import Watchlist
from .ws_client import CameraHub, DeliveryError, DeliveryRejected

log = logging.getLogger("camera-service")
MAX_BODY_BYTES = 64 * 1024


class CameraApp:
    def __init__(self, settings, cameras, watchlist, emitter, hub):
        self.settings = settings
        self.cameras = cameras
        self.watchlist = watchlist
        self.emitter = emitter
        self.hub = hub


class RequestError(Exception):
    def __init__(self, status, detail, extra=None):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.extra = extra or {}


def make_server(app: CameraApp, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "CameraService/1.1"

        def _send(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _check_token(self):
            expected = app.settings.service_token
            if not expected:
                raise RequestError(503, "SERVICE_TOKEN не настроен на сервисе камер")
            given = self.headers.get("X-Service-Token") or ""
            if not hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
                raise RequestError(401, "Неверный токен сервиса")

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise RequestError(400, "Некорректный Content-Length")
            if length > MAX_BODY_BYTES:
                raise RequestError(413, f"Тело больше {MAX_BODY_BYTES} байт")
            raw = self.rfile.read(length) if length else b""
            try:
                data = json.loads(raw.decode("utf-8") or "null")
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise RequestError(400, "Тело должно быть JSON")
            if not isinstance(data, dict):
                raise RequestError(400, "Ожидается JSON-объект")
            return data

        def do_GET(self):
            try:
                path = self.path.split("?")[0]
                if path == "/health":
                    status, payload = 200, {
                        "status": "ok",
                        "cameras": len(app.cameras),
                        "watchlist": len(app.watchlist),
                        "ws_connected": app.hub.connected_count(),
                        "transport": "websocket",
                    }
                elif path == "/v1/cameras":
                    self._check_token()
                    status, payload = 200, {"cameras": [asdict(c) for c in app.cameras]}
                elif path == "/v1/watchlist":
                    self._check_token()
                    plates = app.watchlist.snapshot()
                    status, payload = 200, {"plates": plates, "count": len(plates)}
                else:
                    raise RequestError(404, "Не найдено")
                self._send(status, payload)
            except RequestError as error:
                self._send(error.status, {"detail": error.detail, **error.extra})

        def do_POST(self):
            try:
                path = self.path.split("?")[0]
                if path != "/v1/detections":
                    raise RequestError(404, "Не найдено")
                self._check_token()
                if not app.settings.manual_detections_enabled:
                    raise RequestError(404, "Ручная фиксация отключена")
                data = self._read_json()
                plate = data.get("plate")
                camera_code = data.get("camera_code")
                if not isinstance(plate, str) or not plate.strip():
                    raise RequestError(400, 'Нужно поле "plate"')
                if camera_code is not None and not isinstance(camera_code, str):
                    raise RequestError(400, 'Поле "camera_code" должно быть строкой')
                try:
                    self._send(200, app.emitter.detect(plate, camera_code))
                except UnknownCamera as error:
                    raise RequestError(422, f"Неизвестная или отключённая камера: {error.code}")
                except DeliveryRejected as error:
                    raise RequestError(502, f"Сервис ГИБДД отклонил событие: {error.detail}")
                except DeliveryError as error:
                    raise RequestError(502, f"Сервис ГИБДД недоступен: {error}")
            except RequestError as error:
                self._send(error.status, {"detail": error.detail, **error.extra})

        def do_PUT(self):
            self._send(405, {"detail": "PUT /v1/watchlist отключён: список розыска передаётся по WebSocket"})

        def log_message(self, fmt, *args):
            log.debug("%s - %s", self.address_string(), fmt % args)

    return ThreadingHTTPServer((host, port), Handler)
