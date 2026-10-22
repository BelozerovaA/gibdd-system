import importlib.util
import json
import os
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_PY = os.path.join(BACKEND_DIR, "app", "services", "camera_client.py")

spec = importlib.util.spec_from_file_location("camera_client_under_test", CLIENT_PY)
camera_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(camera_client)


class FakeCameraService:

    def __init__(self, status=200):
        self.requests = []
        self.status = status
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_PUT(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                outer.requests.append({
                    "method": "PUT", "path": self.path,
                    "token": self.headers.get("X-Service-Token"),
                    "content_type": self.headers.get("Content-Type"),
                    "body": json.loads(body.decode("utf-8")),
                })
                self.send_response(outer.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"count": 0}')

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def wait_until(predicate, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PublishOnceTests(unittest.TestCase):
    def setUp(self):
        self.camera = FakeCameraService()
        self.addCleanup(self.camera.close)

    def publisher(self, plates, url=None, token="secret"):
        p = camera_client.WatchlistPublisher(plates_provider=lambda: plates)
        p._base_url, p._token = url or self.camera.url, token
        return p

    def test_request_matches_the_protocol(self):
        ok = self.publisher(["А123ВК43", "Е456КМ43"]).publish_once()
        self.assertTrue(ok)
        request = self.camera.requests[0]
        self.assertEqual(request["method"], "PUT")
        self.assertEqual(request["path"], "/v1/watchlist")
        self.assertEqual(request["body"], {"plates": ["А123ВК43", "Е456КМ43"]})
        self.assertIn("application/json", request["content_type"])

    def test_empty_list_is_sent_too(self):
        self.assertTrue(self.publisher([], token="t").publish_once())
        self.assertEqual(self.camera.requests[0]["body"], {"plates": []})

    def test_token_header_is_sent(self):
        self.publisher(["А1"], token="abc123").publish_once()
        self.assertEqual(self.camera.requests[0]["token"], "abc123")

    def test_trailing_slash_in_base_url_is_ok(self):
        self.publisher(["А1"], url=self.camera.url + "/", token="t").publish_once()
        self.assertEqual(self.camera.requests[0]["path"], "/v1/watchlist")

    def test_rejected_token_means_failure(self):
        self.camera.status = 401
        self.assertFalse(self.publisher(["А1"]).publish_once())

    def test_server_error_means_failure(self):
        self.camera.status = 500
        self.assertFalse(self.publisher(["А1"]).publish_once())

    def test_unreachable_service_does_not_raise(self):
        p = self.publisher(["А1"], url=f"http://127.0.0.1:{free_port()}")
        self.assertFalse(p.publish_once())

    def test_failure_of_plates_provider_does_not_raise(self):
        def broken():
            raise RuntimeError("БД недоступна")
        p = camera_client.WatchlistPublisher(plates_provider=broken)
        p._base_url, p._token = self.camera.url, "t"
        self.assertFalse(p.publish_once())
        self.assertEqual(self.camera.requests, [])


class BackgroundThreadTests(unittest.TestCase):
    def setUp(self):
        self.camera = FakeCameraService()
        self.addCleanup(self.camera.close)
        self.plates = ["А1"]
        self.publisher = camera_client.WatchlistPublisher(plates_provider=lambda: list(self.plates))
        self.addCleanup(self.publisher.stop)

    def test_publishes_immediately_on_start(self):
        self.publisher.start(self.camera.url, "t", resync_seconds=60)
        self.assertTrue(wait_until(lambda: len(self.camera.requests) >= 1))

    def test_kick_publishes_new_list_without_waiting_for_resync(self):
        self.publisher.start(self.camera.url, "t", resync_seconds=60)
        self.assertTrue(wait_until(lambda: len(self.camera.requests) == 1))
        self.plates.append("Б2")
        self.publisher.kick()
        self.assertTrue(wait_until(lambda: len(self.camera.requests) == 2))
        self.assertEqual(self.camera.requests[-1]["body"], {"plates": ["А1", "Б2"]})

    def test_periodic_resync_heals_a_restarted_camera_service(self):
        self.publisher.start(self.camera.url, "t", resync_seconds=0.1)
        self.assertTrue(wait_until(lambda: len(self.camera.requests) >= 3))

    def test_recovers_after_camera_service_comes_back(self):
        self.camera.status = 500
        self.publisher.start(self.camera.url, "t", resync_seconds=0.1)
        self.assertTrue(wait_until(lambda: len(self.camera.requests) >= 2))
        self.camera.status = 200
        self.assertTrue(wait_until(lambda: self.publisher._last_ok is True))

    def test_retries_quickly_when_camera_service_is_not_up_yet(self):
        # полная пауза 60 с, но после неудачи повтор идёт через retry_seconds
        self.camera.status = 503
        self.publisher.start(self.camera.url, "t", resync_seconds=60, retry_seconds=0.05)
        self.assertTrue(wait_until(lambda: len(self.camera.requests) >= 3))
        self.camera.status = 200
        self.assertTrue(wait_until(lambda: self.publisher._last_ok is True))
        count = len(self.camera.requests)
        time.sleep(0.3)  # после успеха снова ждём полную паузу, лишних отправок нет
        self.assertEqual(len(self.camera.requests), count)

    def test_retry_is_never_longer_than_resync(self):
        self.publisher.start(self.camera.url, "t", resync_seconds=2, retry_seconds=10)
        self.assertEqual(self.publisher._retry_seconds, 2)

    def test_stop_terminates_the_thread(self):
        self.publisher.start(self.camera.url, "t", resync_seconds=60)
        self.assertTrue(self.publisher.running)
        self.publisher.stop()
        self.assertFalse(self.publisher.running)

    def test_kick_before_start_is_harmless(self):
        self.publisher.kick()
        self.assertFalse(self.publisher.running)

    def test_start_twice_does_not_create_second_thread(self):
        self.publisher.start(self.camera.url, "t", resync_seconds=60)
        first = self.publisher._thread
        self.publisher.start(self.camera.url, "t", resync_seconds=60)
        self.assertIs(self.publisher._thread, first)


class StartFromEnvTests(unittest.TestCase):
    def setUp(self):
        self.saved = {k: os.environ.get(k) for k in ("CAMERA_SERVICE_URL", "SERVICE_TOKEN", "WATCHLIST_RESYNC_SECONDS")}
        self.addCleanup(self.restore)

    def restore(self):
        for k, v in self.saved.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_not_started_without_url(self):
        os.environ.pop("CAMERA_SERVICE_URL", None)
        p = camera_client.WatchlistPublisher(plates_provider=lambda: [])
        p.start_from_env()
        self.assertFalse(p.running)

    def test_started_with_url_from_environment(self):
        camera = FakeCameraService()
        self.addCleanup(camera.close)
        os.environ.update({"CAMERA_SERVICE_URL": camera.url, "SERVICE_TOKEN": "env-token", "WATCHLIST_RESYNC_SECONDS": "60"})
        p = camera_client.WatchlistPublisher(plates_provider=lambda: ["А1"])
        self.addCleanup(p.stop)
        p.start_from_env()
        self.assertTrue(wait_until(lambda: len(camera.requests) >= 1))
        self.assertEqual(camera.requests[0]["token"], "env-token")


if __name__ == "__main__":
    unittest.main()
