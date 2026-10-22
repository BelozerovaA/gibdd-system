"""WebSocket-клиенты камер: по одному постоянному соединению на каждую камеру."""
from __future__ import annotations

import json
import logging
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

log = logging.getLogger("camera-service")

try:
    import websocket
except ImportError:  # pragma: no cover
    websocket = None


class DeliveryError(Exception):
    pass


class DeliveryRejected(DeliveryError):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


def _http_to_ws(url: str) -> str:
    url = url.rstrip("/")
    if url.startswith("https://"):
        return "wss://" + url[len("https://"):]
    if url.startswith("http://"):
        return "ws://" + url[len("http://"):]
    if url.startswith("ws://") or url.startswith("wss://"):
        return url
    return "ws://" + url


class CameraSocket:
    def __init__(self, camera_code, base_ws_url, token, on_watchlist, reconnect_delay=2.0):
        self.camera_code = camera_code
        self.url = f"{base_ws_url.rstrip('/')}/ws/cameras/{quote(camera_code, safe='')}?token={quote(token, safe='')}"
        self.on_watchlist = on_watchlist
        self.reconnect_delay = reconnect_delay
        self._ws = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._thread = None
        self._pending = {}
        self._results = {}
        self._results_lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, name=f"ws-{self.camera_code}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._connected.clear()
        with self._lock:
            ws = self._ws
            self._ws = None
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=3)

    def send_detection(self, event: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        if not self._connected.wait(timeout=timeout):
            raise DeliveryError(f"камера {self.camera_code}: нет WebSocket-соединения")
        event_id = event["event_id"]
        payload = {
            "type": "detection",
            "event_id": event_id,
            "plate": event["plate"],
            "camera_code": self.camera_code,
            "detected_at": event["detected_at"],
        }
        done = threading.Event()
        with self._results_lock:
            self._pending[event_id] = done
            self._results.pop(event_id, None)
        with self._lock:
            ws = self._ws
        if ws is None:
            with self._results_lock:
                self._pending.pop(event_id, None)
            raise DeliveryError(f"камера {self.camera_code}: соединение закрыто")
        try:
            ws.send(json.dumps(payload, ensure_ascii=False))
        except Exception as error:
            with self._results_lock:
                self._pending.pop(event_id, None)
            raise DeliveryError(f"камера {self.camera_code}: отправка не удалась: {error}")
        if not done.wait(timeout=timeout):
            with self._results_lock:
                self._pending.pop(event_id, None)
            raise DeliveryError(f"камера {self.camera_code}: нет ответа (ack) за {timeout} с")
        with self._results_lock:
            result = self._results.pop(event_id, {"status": "error", "detail": "no_result"})
            self._pending.pop(event_id, None)
        if result.get("status") == "error":
            raise DeliveryRejected(result.get("detail", "error"))
        return result

    def _run_loop(self) -> None:
        if websocket is None:
            log.error("Пакет websocket-client не установлен: pip install websocket-client")
            return
        delay = self.reconnect_delay
        while not self._stop.is_set():
            try:
                self._session()
            except Exception as error:
                log.warning("Камера %s: обрыв WS: %s", self.camera_code, error)
            self._connected.clear()
            if self._stop.is_set():
                break
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 1.5, 30.0)

    def _session(self) -> None:
        log.info("Камера %s: подключение к %s", self.camera_code, self.url.split("?")[0])

        def on_message(ws, message: str) -> None:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                return
            msg_type = data.get("type")
            if msg_type == "watchlist":
                plates = data.get("plates") or []
                if isinstance(plates, list):
                    self.on_watchlist([str(p) for p in plates])
            elif msg_type == "ack":
                event_id = str(data.get("event_id") or "")
                with self._results_lock:
                    self._results[event_id] = data
                    ev = self._pending.get(event_id)
                if ev is not None:
                    ev.set()
            elif msg_type == "error":
                log.warning("Камера %s: ошибка от backend: %s", self.camera_code, data.get("detail"))

        def on_open(ws) -> None:
            log.info("Камера %s: WebSocket открыт", self.camera_code)
            with self._lock:
                self._ws = ws
            self._connected.set()

        def on_close(ws, status, msg) -> None:
            log.info("Камера %s: WebSocket закрыт (%s)", self.camera_code, status)
            self._connected.clear()
            with self._lock:
                if self._ws is ws:
                    self._ws = None

        def on_error(ws, error) -> None:
            log.warning("Камера %s: WS error: %s", self.camera_code, error)

        ws = websocket.WebSocketApp(self.url, on_message=on_message, on_open=on_open, on_close=on_close, on_error=on_error)
        with self._lock:
            self._ws = ws
        ws.run_forever(ping_interval=25, ping_timeout=10)


class CameraHub:
    def __init__(self, camera_codes, gibdd_url, token, on_watchlist):
        base = _http_to_ws(gibdd_url)
        self._sockets = {
            code: CameraSocket(code, base, token, on_watchlist) for code in camera_codes
        }

    def start(self) -> None:
        for sock in self._sockets.values():
            sock.start()

    def stop(self) -> None:
        for sock in self._sockets.values():
            sock.stop()

    def get(self, camera_code: str) -> Optional[CameraSocket]:
        return self._sockets.get(camera_code)

    def connected_count(self) -> int:
        return sum(1 for s in self._sockets.values() if s.connected)
