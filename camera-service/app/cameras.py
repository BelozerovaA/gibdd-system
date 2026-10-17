"""Список камер: где стоят и какие адреса контролируют."""
import json
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Camera:
    code: str            # «CAM-08»; по этому коду сервис ГИБДД находит камеру у себя
    address: str
    latitude: float
    longitude: float
    type: str
    speed_limit: int
    active: bool


def load_cameras(path: str) -> List[Camera]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    items = raw.get("cameras") if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError(f'В файле {path} должен быть ключ "cameras" со списком камер')

    cameras, seen = [], set()
    for index, item in enumerate(items, start=1):
        try:
            camera = Camera(
                code=str(item["code"]).strip(),
                address=str(item["address"]).strip(),
                latitude=float(item["latitude"]),
                longitude=float(item["longitude"]),
                type=str(item.get("type", "")),
                speed_limit=int(item.get("speed_limit", 0)),
                active=bool(item.get("active", True)),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Камера №{index} в {path} заполнена неверно: {error!r}")
        if not camera.code or not camera.address:
            raise ValueError(f"У камеры №{index} в {path} пустой код или адрес")
        if camera.code in seen:
            raise ValueError(f'Код камеры "{camera.code}" повторяется в {path}')
        seen.add(camera.code)
        cameras.append(camera)
    return cameras


def find_camera(cameras: List[Camera], code: str) -> Optional[Camera]:
    return next((c for c in cameras if c.code == code), None)
