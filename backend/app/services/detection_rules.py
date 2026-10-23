from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

ALERT_DATE_FORMAT = "%d.%m.%Y"
ALERT_TIME_FORMAT = "%H:%M:%S"
IGNORE_NOT_WANTED = "not_wanted"
IGNORE_PENDING = "pending_alert"
IGNORE_COOLDOWN = "cooldown"
IGNORE_DUPLICATE = "duplicate"

REACTION_WAITING = "Ожидает"

def normalize_plate(plate: str) -> str:
    return "".join(plate.split()).upper()

def camera_number(camera_code: str, fallback: int) -> int:
    digits = "".join(ch for ch in (camera_code or "") if ch.isdigit())
    return int(digits) if digits else fallback

def to_local_time(moment: datetime, timezone_name: str) -> datetime:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = timezone(timedelta(hours=3))
    return moment.astimezone(zone).replace(tzinfo=None)


def format_alert_moment(moment: datetime) -> Tuple[str, str]:
    return moment.strftime(ALERT_DATE_FORMAT), moment.strftime(ALERT_TIME_FORMAT)


def parse_alert_moment(date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.strptime(f"{date_str} {time_str}", f"{ALERT_DATE_FORMAT} {ALERT_TIME_FORMAT}")
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class LastAlert:
    reaction_status: Optional[str]
    created_at: Optional[datetime]


def decide(
    is_wanted: bool,
    last_alert: Optional[LastAlert],
    moment: datetime,
    cooldown_seconds: int,
) -> Optional[str]:
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
