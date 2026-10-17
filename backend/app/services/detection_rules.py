"""Правила обработки события «камера увидела автомобиль».

Модуль не зависит ни от базы данных, ни от FastAPI: только чистые функции и маленькие
классы. Благодаря этому правила проверяются обычными тестами (backend/tests), а работа
с БД вынесена в services/detections.py.
"""
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

ALERT_DATE_FORMAT = "%d.%m.%Y"
ALERT_TIME_FORMAT = "%H:%M:%S"

# Причины, по которым событие принято, но оповещение не создаётся (попадают в ответ камерам)
IGNORE_NOT_WANTED = "not_wanted"
IGNORE_PENDING = "pending_alert"
IGNORE_COOLDOWN = "cooldown"
IGNORE_DUPLICATE = "duplicate"

# Реакция сотрудника, означающая «ещё не ответил» (то же значение хранится в таблице alerts)
REACTION_WAITING = "Ожидает"


def normalize_plate(plate: str) -> str:
    """ГРЗ без пробелов и в верхнем регистре: « а123вк43 » -> «А123ВК43»."""
    return "".join(plate.split()).upper()


def camera_number(camera_code: str, fallback: int) -> int:
    """Номер камеры на карте: «CAM-08» -> 8. Если цифр нет, берётся запасное значение."""
    digits = "".join(ch for ch in (camera_code or "") if ch.isdigit())
    return int(digits) if digits else fallback


def to_local_time(moment: datetime, timezone_name: str) -> datetime:
    """Переводит момент фиксации в местное время (без указания пояса).

    Камеры присылают время с поясом, обычно в UTC. Если пояса нет, считаем, что это UTC.
    Если базы часовых поясов нет в системе (например, на Windows без пакета tzdata),
    используется московское время UTC+3.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = timezone(timedelta(hours=3))
    return moment.astimezone(zone).replace(tzinfo=None)


def format_alert_moment(moment: datetime) -> Tuple[str, str]:
    """Дата и время в том виде, в котором они хранятся в БД: («03.10.2026», «12:00:00»)."""
    return moment.strftime(ALERT_DATE_FORMAT), moment.strftime(ALERT_TIME_FORMAT)


def parse_alert_moment(date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
    """Обратное преобразование. Для повреждённых значений возвращает None."""
    try:
        return datetime.strptime(f"{date_str} {time_str}", f"{ALERT_DATE_FORMAT} {ALERT_TIME_FORMAT}")
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class LastAlert:
    """Последнее оповещение по записи розыска: что нужно знать, чтобы не засыпать сотрудника."""
    reaction_status: Optional[str]
    created_at: Optional[datetime]


def decide(
    is_wanted: bool,
    last_alert: Optional[LastAlert],
    moment: datetime,
    cooldown_seconds: int,
) -> Optional[str]:
    """Решает, создавать ли оповещение. None означает «создавать», иначе причина отказа.

    1. Автомобиля нет среди активных записей розыска: оповещение не нужно.
    2. По записи уже есть оповещение, на которое сотрудник не ответил: второе не создаём.
    3. Предыдущее оповещение было совсем недавно (cooldown_seconds): даём сотруднику
       время ответить, прежде чем снова его беспокоить. Это заменяет прежнюю «паузу
       симулятора», которая действовала, пока сотрудник не ответит.
    """
    if not is_wanted:
        return IGNORE_NOT_WANTED
    if last_alert is not None:
        if last_alert.reaction_status == REACTION_WAITING:
            return IGNORE_PENDING
        if last_alert.created_at is not None:
            elapsed = (moment - last_alert.created_at).total_seconds()
            if elapsed < cooldown_seconds:
                return IGNORE_COOLDOWN
    return None


class EventDeduplicator:
    """Помнит последние идентификаторы событий, чтобы повторная отправка того же события
    (камера не получила ответ и отправила снова) не создала второе оповещение."""

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._seen: "OrderedDict[str, None]" = OrderedDict()
        self._lock = Lock()

    def contains(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._seen

    def add(self, event_id: str) -> None:
        with self._lock:
            self._seen[event_id] = None
            self._seen.move_to_end(event_id)
            while len(self._seen) > self._max_size:
                self._seen.popitem(last=False)
