"""Оба сервиса вместе, по протоколу, с реальным кодом с обеих сторон.

  сервис ГИБДД (заглушка вместо БД)  --PUT /v1/watchlist-->  сервис камер (настоящий)
  сервис ГИБДД (заглушка вместо БД)  <--POST /api/camera-events--  сервис камер (настоящий)

Что настоящее: сервер и эмиттер сервиса камер, отправитель списка (services/camera_client.py)
и правила решений (services/detection_rules.py) из backend. Что заглушка: база данных.
Тест показывает, что изменение розыска доходит до камер, а камеры видят только то, что нужно.
"""
import importlib.util
import json
import os
import threading
import unittest
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.cameras import load_cameras
from app.config import load_settings
from app.emitter import Emitter
from app.gibdd_client import GibddClient
from app.server import CameraApp, make_server
from app.watchlist import Watchlist
from tests.fakes import wait_until

SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_APP = os.path.join(os.path.dirname(SERVICE_DIR), "backend", "app", "services")
TOKEN = "e2e-token"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(BACKEND_APP, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(os.path.isdir(BACKEND_APP), "папка backend не найдена")
class EndToEndTests(unittest.TestCase):
    COOLDOWN = 120

    def setUp(self):
        self.rules = load("rules_e2e", "detection_rules.py")
        self.client_module = load("camera_client_e2e", "camera_client.py")

        # --- «сервис ГИБДД»: розыск в памяти + настоящие правила решений
        self.wanted = {"А111АА43", "Б222ББ43"}
        self.alerts = []          # созданные оповещения
        self.ignored = []         # причины отказов
        self.lock = threading.Lock()
        self.dedup = self.rules.EventDeduplicator()
        outer = self

        class Gibdd(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
                if self.headers.get("X-Service-Token") != TOKEN:
                    return self._reply(401, {"detail": "Неверный токен сервиса"})
                with outer.lock:
                    if outer.dedup.contains(body["event_id"]):
                        return self._reply(200, {"status": "ignored", "reason": "duplicate"})
                    moment = self.rules_local(body["detected_at"])
                    plate = outer.rules.normalize_plate(body["plate"])
                    last = None
                    mine = [a for a in outer.alerts if a["plate"] == plate]
                    if mine:
                        last = outer.rules.LastAlert(mine[-1]["reaction"], mine[-1]["at"])
                    reason = outer.rules.decide(plate in outer.wanted, last, moment, outer.COOLDOWN)
                    outer.dedup.add(body["event_id"])
                    if reason:
                        outer.ignored.append(reason)
                        return self._reply(200, {"status": "ignored", "reason": reason})
                    outer.alerts.append({"plate": plate, "camera": body["camera_code"], "reaction": "Ожидает", "at": moment})
                    return self._reply(200, {"status": "accepted", "alert_id": len(outer.alerts)})

            def rules_local(self, iso):
                return outer.rules.to_local_time(datetime.fromisoformat(iso), "Europe/Moscow")

            def _reply(self, status, payload):
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.gibdd = ThreadingHTTPServer(("127.0.0.1", 0), Gibdd)
        threading.Thread(target=self.gibdd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        gibdd_url = f"http://127.0.0.1:{self.gibdd.server_address[1]}"

        # --- настоящий сервис камер
        settings = load_settings({"GIBDD_URL": gibdd_url, "SERVICE_TOKEN": TOKEN, "DELIVERY_ATTEMPTS": "1"})
        cameras = load_cameras(os.path.join(SERVICE_DIR, "app", "cameras.json"))
        self.watchlist = Watchlist()
        client = GibddClient(gibdd_url, TOKEN, timeout=2, attempts=1)
        self.emitter = Emitter(cameras, self.watchlist, client, interval=0.03)
        self.camera_server = make_server(CameraApp(settings, cameras, self.watchlist, self.emitter), "127.0.0.1", 0)
        threading.Thread(target=self.camera_server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        camera_url = f"http://127.0.0.1:{self.camera_server.server_address[1]}"

        # --- настоящий отправитель списка из backend, читает «розыск» заглушки
        self.publisher = self.client_module.WatchlistPublisher(plates_provider=lambda: sorted(self.wanted))
        self.publisher.start(camera_url, TOKEN, resync_seconds=60, retry_seconds=0.05)

        self.stop_emitter = threading.Event()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.stop_emitter.set()
        self.publisher.stop()
        for server in (self.gibdd, self.camera_server):
            server.shutdown(); server.server_close()

    def start_cameras(self):
        threading.Thread(target=self.emitter.run, args=(self.stop_emitter,), daemon=True).start()

    def test_wanted_list_reaches_cameras(self):
        self.assertTrue(wait_until(lambda: self.watchlist.snapshot() == ["А111АА43", "Б222ББ43"]))

    def test_cameras_report_only_wanted_vehicles_and_alert_is_created(self):
        self.assertTrue(wait_until(lambda: len(self.watchlist) == 2))
        self.start_cameras()
        self.assertTrue(wait_until(lambda: len(self.alerts) >= 1))
        self.assertTrue({a["plate"] for a in self.alerts} <= {"А111АА43", "Б222ББ43"})
        self.assertTrue(all(a["camera"].startswith("CAM-") for a in self.alerts))

    def test_second_alert_for_the_same_plate_is_held_back_until_answered(self):
        self.wanted = {"А111АА43"}
        self.publisher.kick()
        self.assertTrue(wait_until(lambda: self.watchlist.snapshot() == ["А111АА43"]))
        self.start_cameras()
        self.assertTrue(wait_until(lambda: len(self.alerts) == 1))
        self.assertTrue(wait_until(lambda: "pending_alert" in self.ignored))  # камеры продолжают, но оповещение одно
        self.assertEqual(len(self.alerts), 1)
        # сотрудник ответил, а пауза (cooldown) отключена: оповещения возможны снова
        with self.lock:
            self.alerts[0]["reaction"] = "Принято"
            self.COOLDOWN = 0
        self.assertTrue(wait_until(lambda: len(self.alerts) >= 2))

    def test_added_vehicle_is_picked_up_and_removed_vehicle_is_dropped(self):
        self.wanted = {"А111АА43"}
        self.publisher.kick()
        self.assertTrue(wait_until(lambda: self.watchlist.snapshot() == ["А111АА43"]))
        self.wanted = {"Б222ББ43"}   # розыск по первой машине снят, по второй открыт
        self.publisher.kick()
        self.assertTrue(wait_until(lambda: self.watchlist.snapshot() == ["Б222ББ43"]))
        self.start_cameras()
        self.assertTrue(wait_until(lambda: len(self.alerts) >= 1))
        self.assertEqual({a["plate"] for a in self.alerts}, {"Б222ББ43"})

    def test_manual_detection_of_a_vehicle_that_is_not_wanted_is_ignored(self):
        result = self.emitter.detect("Х999ХХ43", "CAM-08")
        self.assertEqual(result["gibdd_response"], {"status": "ignored", "reason": "not_wanted"})
        self.assertEqual(self.alerts, [])

    def test_manual_detection_creates_alert_with_local_time(self):
        result = self.emitter.detect(" а111аа43 ", "CAM-08")
        self.assertEqual(result["gibdd_response"]["status"], "accepted")
        self.assertEqual(self.alerts[0]["plate"], "А111АА43")
        delta = abs((self.alerts[0]["at"] - datetime.now()).total_seconds())
        self.assertLess(delta, 24 * 3600)  # время переведено в местное, а не перепутано днями

    def test_wrong_token_is_rejected_by_gibdd(self):
        bad = GibddClient(f"http://127.0.0.1:{self.gibdd.server_address[1]}", "bad-token", attempts=1)
        from app.gibdd_client import DeliveryRejected
        with self.assertRaises(DeliveryRejected) as ctx:
            bad.send_detection({"event_id": "x1", "plate": "А111АА43", "camera_code": "CAM-01", "detected_at": datetime.now().astimezone().isoformat()})
        self.assertEqual(ctx.exception.status, 401)


if __name__ == "__main__":
    unittest.main()
