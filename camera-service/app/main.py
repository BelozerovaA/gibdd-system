"""Точка входа сервиса камер:  python -m app.main"""
import logging
import signal
import sys
import threading

from .cameras import load_cameras
from .config import ConfigError, load_settings
from .emitter import Emitter
from .gibdd_client import GibddClient
from .server import CameraApp, make_server
from .watchlist import Watchlist

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
        log.warning("SERVICE_TOKEN не задан: сервис камер не сможет ни принимать список розыска, "
                    "ни отправлять события в сервис ГИБДД")

    watchlist = Watchlist()
    client = GibddClient(
        settings.gibdd_url,
        settings.service_token,
        timeout=settings.request_timeout,
        attempts=settings.delivery_attempts,
        retry_delay=settings.retry_delay,
    )
    emitter = Emitter(cameras, watchlist, client, settings.interval_seconds)
    server = make_server(CameraApp(settings, cameras, watchlist, emitter), settings.host, settings.port)

    stop = threading.Event()
    threading.Thread(target=emitter.run, args=(stop,), name="emitter", daemon=True).start()

    def shutdown(signum, frame):
        log.info("Получен сигнал %s, останавливаюсь", signum)
        stop.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log.info("Сервис камер запущен на %s:%s, камер: %s, сервис ГИБДД: %s",
             settings.host, settings.port, len(cameras), settings.gibdd_url)
    server.serve_forever()
    server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
