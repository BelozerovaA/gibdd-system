from threading import Lock
from typing import Iterable, List

def normalize_plate(plate: str) -> str:
    return "".join(str(plate).split()).upper()


class Watchlist:
    def __init__(self) -> None:
        self._plates: set = set()
        self._lock = Lock()

    def replace(self, plates: Iterable[str]) -> int:
        cleaned = {normalize_plate(p) for p in plates}
        cleaned.discard("")
        with self._lock:
            self._plates = cleaned
            return len(cleaned)

    def snapshot(self) -> List[str]:
        with self._lock:
            return sorted(self._plates)

    def __len__(self) -> int:
        with self._lock:
            return len(self._plates)
