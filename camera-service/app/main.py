from __future__ import annotations

import logging
import signal
import sys
import threading

from .cameras import load_cameras
from .config import ConfigError, load_settings
from .emitter import Emitter
from .server import CameraApp, make_server
from .watchlist import Watchlist
from .ws_client import CameraHub

log = logging.getLogger("camera-service")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = load_settings()
        cameras = load_cameras(settings.cameras_file)
    except (ConfigError, ValueError, OSError) as error:
        log.error("Не удалось запустить сервис камер: %s", error)
        return 2

    if not settings.service_token:
        log.warning("SERVICE_TOKEN не задан: камеры не смогут подключиться к ГИБДД по WebSocket")

    watchlist = Watchlist()

    def on_watchlist(plates):
        n = watchlist.replace(plates)
        log.info("Получен watchlist по WebSocket: %s ГРЗ", n)

    active_codes = [c.code for c in cameras if c.active]
    hub = CameraHub(active_codes, settings.gibdd_url, settings.service_token, on_watchlist)
    emitter = Emitter(cameras, watchlist, hub, settings.interval_seconds)
    server = make_server(CameraApp(settings, cameras, watchlist, emitter, hub), settings.host, settings.port)

    stop = threading.Event()
    hub.start()
    threading.Thread(target=emitter.run, args=(stop,), name="emitter", daemon=True).start()

    def shutdown(signum, frame):
        log.info("Получен сигнал %s, останавливаюсь", signum)
        stop.set()
        hub.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log.info(
        "Сервис камер на %s:%s, камер: %s, ГИБДД: %s (WebSocket, 1 соединение на камеру)",
        settings.host, settings.port, len(cameras), settings.gibdd_url,
    )
    server.serve_forever()
    server.server_close()
    hub.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
