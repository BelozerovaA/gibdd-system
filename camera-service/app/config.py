"""Настройки сервиса камер. Всё берётся из переменных окружения."""
import os
from dataclasses import dataclass
from typing import Mapping, Optional


class ConfigError(Exception):
    """Переменная окружения задана неверно."""


@dataclass(frozen=True)
class Settings:
    gibdd_url: str                 
    service_token: str             
    interval_seconds: float        
    host: str
    port: int
    cameras_file: str
    request_timeout: float         
    delivery_attempts: int         
    retry_delay: float             
    manual_detections_enabled: bool  


def _number(env: Mapping[str, str], name: str, default: float, minimum: float, cast=float):
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = cast(raw)
    except ValueError:
        raise ConfigError(f"{name}={raw!r}: ожидается число")
    if value < minimum:
        raise ConfigError(f"{name}={raw}: значение не может быть меньше {minimum}")
    return value


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise ConfigError(f"{name}={raw!r}: ожидается true или false")


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    env = os.environ if env is None else env
    default_cameras = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cameras.json")
    return Settings(
        gibdd_url=env.get("GIBDD_URL", "http://localhost:8000").strip().rstrip("/"),
        service_token=env.get("SERVICE_TOKEN", "").strip(),
        interval_seconds=_number(env, "CAMERA_INTERVAL_SECONDS", 60.0, 0.1),
        host=env.get("HOST", "0.0.0.0").strip() or "0.0.0.0",
        port=int(_number(env, "PORT", 9000, 1, cast=int)),
        cameras_file=env.get("CAMERAS_FILE", "").strip() or default_cameras,
        request_timeout=_number(env, "REQUEST_TIMEOUT_SECONDS", 5.0, 0.1),
        delivery_attempts=int(_number(env, "DELIVERY_ATTEMPTS", 3, 1, cast=int)),
        retry_delay=_number(env, "RETRY_DELAY_SECONDS", 1.0, 0.0),
        manual_detections_enabled=_flag(env, "ENABLE_MANUAL_DETECTIONS", True),
    )
