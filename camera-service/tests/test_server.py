"""HTTP-интерфейс сервиса камер: запускается настоящий сервер на свободном порту."""
import json
import os
import threading
import unittest
import urllib.error
import urllib.request

from app.cameras import load_cameras
from app.config import load_settings
from app.emitter import Emitter
from app.gibdd_client import GibddClient
from app.server import CameraApp, make_server
from app.watchlist import Watchlist
from tests.fakes import FakeGibdd

PACKAGED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "cameras.json")
TOKEN = "test-token"


class ServerTestCase(unittest.TestCase):
    manual = "true"
    token = TOKEN

    def setUp(self):
        self.gibdd = FakeGibdd(); self.addCleanup(self.gibdd.close)
        settings = load_settings({"GIBDD_URL": self.gibdd.url, "SERVICE_TOKEN": self.token,
                                  "ENABLE_MANUAL_DETECTIONS": self.manual, "DELIVERY_ATTEMPTS": "1"})
        cameras = load_cameras(PACKAGED)
        self.watchlist = Watchlist()
        client = GibddClient(settings.gibdd_url, settings.service_token, timeout=2, attempts=1)
        emitter = Emitter(cameras, self.watchlist, client, 60)
        self.server = make_server(CameraApp(settings, cameras, self.watchlist, emitter), "127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown(); self.server.server_close()

    def call(self, method, path, body=None, token=TOKEN, raw=None, headers=None):
        data = raw if raw is not None else (json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None)
        h = {"Content-Type": "application/json"}
        if token is not None:
            h["X-Service-Token"] = token
        h.update(headers or {})
        request = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(request, timeout=3) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))


class PublicAndAuthTests(ServerTestCase):
    def test_health_is_public(self):
        status, body = self.call("GET", "/health", token=None)
        self.assertEqual((status, body["status"], body["cameras"], body["watchlist"]), (200, "ok", 15, 0))

    def test_protected_routes_need_the_token(self):
        for method, path in (("GET", "/v1/cameras"), ("GET", "/v1/watchlist"), ("PUT", "/v1/watchlist"), ("POST", "/v1/detections")):
            self.assertEqual(self.call(method, path, {}, token=None)[0], 401, path)
            self.assertEqual(self.call(method, path, {}, token="wrong-token")[0], 401, path)

    def test_unknown_path_and_wrong_method(self):
        self.assertEqual(self.call("GET", "/v1/nothing")[0], 404)
        self.assertEqual(self.call("DELETE", "/v1/watchlist")[0], 405)
        self.assertEqual(self.call("GET", "/v1/detections")[0], 405)

    def test_trailing_slash_is_accepted(self):
        self.assertEqual(self.call("GET", "/v1/watchlist/")[0], 200)


class NoTokenConfiguredTests(ServerTestCase):
    token = ""

    def test_everything_protected_is_closed(self):
        status, body = self.call("GET", "/v1/watchlist", token="any-token")
        self.assertEqual(status, 503)
        self.assertIn("SERVICE_TOKEN", body["detail"])
        self.assertEqual(self.call("GET", "/health", token=None)[0], 200)


class WatchlistTests(ServerTestCase):
    def test_put_replaces_and_get_returns(self):
        self.assertEqual(self.call("PUT", "/v1/watchlist", {"plates": ["а123вк43", "Е456КМ43", "А123ВК43"]}), (200, {"count": 2}))
        status, body = self.call("GET", "/v1/watchlist")
        self.assertEqual((status, body), (200, {"plates": ["А123ВК43", "Е456КМ43"], "count": 2}))
        self.call("PUT", "/v1/watchlist", {"plates": []})
        self.assertEqual(self.call("GET", "/v1/watchlist")[1]["count"], 0)

    def test_validation(self):
        bad = ({}, {"plates": "А1"}, {"plates": [1]}, {"plates": [""]}, {"plates": ["А" * 21]}, {"plates": ["А1"] * 5001})
        for body in bad:
            self.assertEqual(self.call("PUT", "/v1/watchlist", body)[0], 400, str(body)[:40])
        self.assertEqual(len(self.watchlist), 0)  # неверный запрос список не меняет

    def test_broken_json_and_non_object(self):
        self.assertEqual(self.call("PUT", "/v1/watchlist", raw=b"{ni json")[0], 400)
        self.assertEqual(self.call("PUT", "/v1/watchlist", raw=b"[1,2]")[0], 400)
        self.assertEqual(self.call("PUT", "/v1/watchlist", raw=b"")[0], 400)

    def test_too_large_body(self):
        self.assertEqual(self.call("PUT", "/v1/watchlist", raw=b"x" * (70 * 1024))[0], 413)


class CamerasTests(ServerTestCase):
    def test_lists_all_cameras(self):
        status, body = self.call("GET", "/v1/cameras")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["cameras"]), 15)
        self.assertEqual(body["cameras"][0]["code"], "CAM-01")


class ManualDetectionTests(ServerTestCase):
    def test_event_reaches_gibdd(self):
        status, body = self.call("POST", "/v1/detections", {"plate": "а123вк43", "camera_code": "CAM-08"})
        self.assertEqual(status, 200)
        self.assertEqual(body["gibdd_response"]["status"], "accepted")
        sent = self.gibdd.requests[0]
        self.assertEqual(sent["token"], TOKEN)
        self.assertEqual((sent["body"]["plate"], sent["body"]["camera_code"]), ("А123ВК43", "CAM-08"))

    def test_camera_is_optional(self):
        self.assertEqual(self.call("POST", "/v1/detections", {"plate": "А1"})[0], 200)
        self.assertTrue(self.gibdd.requests[0]["body"]["camera_code"].startswith("CAM-"))

    def test_validation(self):
        self.assertEqual(self.call("POST", "/v1/detections", {})[0], 400)
        self.assertEqual(self.call("POST", "/v1/detections", {"plate": ""})[0], 400)
        self.assertEqual(self.call("POST", "/v1/detections", {"plate": "А1", "camera_code": 5})[0], 400)
        self.assertEqual(self.gibdd.requests, [])

    def test_unknown_camera(self):
        status, body = self.call("POST", "/v1/detections", {"plate": "А1", "camera_code": "CAM-99"})
        self.assertEqual(status, 422)
        self.assertIn("CAM-99", body["detail"])
        self.assertEqual(self.gibdd.requests, [])

    def test_gibdd_unavailable_gives_502(self):
        self.gibdd.responses = [(500, {"detail": "сбой"})]
        status, body = self.call("POST", "/v1/detections", {"plate": "А1", "camera_code": "CAM-01"})
        self.assertEqual(status, 502)
        self.assertIn("недоступен", body["detail"])

    def test_gibdd_rejection_is_reported_with_its_status(self):
        self.gibdd.responses = [(401, {"detail": "Неверный токен сервиса"})]
        status, body = self.call("POST", "/v1/detections", {"plate": "А1", "camera_code": "CAM-01"})
        self.assertEqual((status, body["gibdd_status"]), (502, 401))
        self.assertIn("Неверный токен", body["detail"])

    def test_ignored_by_gibdd_is_passed_through(self):
        self.gibdd.responses = [(200, {"status": "ignored", "reason": "not_wanted"})]
        status, body = self.call("POST", "/v1/detections", {"plate": "А1"})
        self.assertEqual((status, body["gibdd_response"]["reason"]), (200, "not_wanted"))


class ManualDisabledTests(ServerTestCase):
    manual = "false"

    def test_endpoint_is_off(self):
        self.assertEqual(self.call("POST", "/v1/detections", {"plate": "А1"})[0], 404)
        self.assertEqual(self.gibdd.requests, [])


if __name__ == "__main__":
    unittest.main()
