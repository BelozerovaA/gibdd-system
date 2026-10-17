import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict


class DeliveryError(Exception):
    """Не удалось доставить событие в сервис ГИБДД (сеть, 5xx)."""


class DeliveryRejected(DeliveryError):
    """Сервис ГИБДД получил событие, но отклонил его (4xx)."""

    def __init__(self, status: int, detail: str):
        super().__init__(f"сервис ГИБДД ответил {status}: {detail}")
        self.status = status
        self.detail = detail


class GibddClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 5.0,
        attempts: int = 3,
        retry_delay: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.attempts = max(1, attempts)
        self.retry_delay = retry_delay
        self._sleep = sleep

    def _request(self, event: Dict[str, Any]) -> urllib.request.Request:
        return urllib.request.Request(
            url=f"{self.base_url}/api/camera-events",
            data=json.dumps(event, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Service-Token": self.token,
            },
        )

    def send_detection(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Отправляет событие и возвращает ответ сервиса ГИБДД (словарь)."""
        last_error = "нет ответа"
        for attempt in range(1, self.attempts + 1):
            try:
                with urllib.request.urlopen(self._request(event), timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8") or "{}"
                    return json.loads(raw)
            except urllib.error.HTTPError as error:
                detail = _read_detail(error)
                if 400 <= error.code < 500:
                    raise DeliveryRejected(error.code, detail)
                last_error = f"HTTP {error.code}: {detail}"
            except (urllib.error.URLError, OSError, ValueError) as error:
                last_error = str(error)

            if attempt < self.attempts:
                self._sleep(self.retry_delay * attempt)

        raise DeliveryError(f"не удалось отправить за {self.attempts} попыток: {last_error}")


def _read_detail(error: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(error.read().decode("utf-8"))
        detail = body.get("detail") if isinstance(body, dict) else None
        return str(detail) if detail else error.reason
    except Exception:
        return str(error.reason)
