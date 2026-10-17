"""Проверка токена, которым сервисы подтверждают друг друга (сервис камер -> сервис ГИБДД)."""
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, status


def require_service_token(x_service_token: Optional[str] = Header(default=None)) -> None:
    """Зависимость FastAPI: пропускает запрос, только если заголовок X-Service-Token верный.

    Токен читается при каждом запросе из переменной SERVICE_TOKEN. Если она не задана,
    приём событий закрыт целиком (503): лучше отказать, чем пустить кого угодно.
    """
    expected = os.getenv("SERVICE_TOKEN", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SERVICE_TOKEN не настроен на сервере",
        )
    if not x_service_token or not hmac.compare_digest(
        x_service_token.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен сервиса",
        )
