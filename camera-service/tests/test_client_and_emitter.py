"""Клиент отправки событий (повторы) и эмиттер (что и когда отправляется)."""
import random
import socket
import threading
import unittest
from datetime import datetime

from app.cameras import Camera
from app.emitter import Emitter, UnknownCamera, build_event
from app.gibdd_client import DeliveryError, DeliveryRejected, GibddClient
from app.watchlist import Watchlist
from tests.fakes import FakeGibdd, wait_until

EVENT = {"event_id": "e1", "plate": "А123ВК43", "camera_code": "CAM-08", "detected_at": "2026-10-12T09:00:00+00:00"}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def camera(code, active=True):
    return Camera(code=code, address=f"ул. {code}", latitude=1.0, longitude=2.0, type="Стационарная", speed_limit=60, active=active)


class ClientTests(unittest.TestCase):
    def client(self, url, **kw):
        sleeps = []
        c = GibddClient(url, "tok", timeout=2, retry_delay=0.5, sleep=sleeps.append, **kw)
        c.sleeps = sleeps
        return c

    def test_request_matches_the_protocol(self):
        gibdd = FakeGibdd(); self.addCleanup(gibdd.close)
        result = self.client(gibdd.url, attempts=3).send_detection(EVENT)
        self.assertEqual(result["status"], "accepted")
        sent = gibdd.requests[0]
        self.assertEqual(sent["path"], "/api/camera-events")
        self.assertEqual(sent["body"], EVENT)
        self.assertIn("application/json", sent["content_type"])
        self.assertEqual(sent["token"], "tok")

    def test_retries_on_server_error_with_the_same_event_id(self):
        gibdd = FakeGibdd([(500, {"detail": "сбой"}), (503, {"detail": "занят"}), (200, {"status": "accepted"})])
        self.addCleanup(gibdd.close)
        c = self.client(gibdd.url, attempts=3)
        self.assertEqual(c.send_detection(EVENT)["status"], "accepted")
        self.assertEqual(len(gibdd.requests), 3)
        self.assertEqual({r["body"]["event_id"] for r in gibdd.requests}, {"e1"})  # повтор идемпотентен
        self.assertEqual(c.sleeps, [0.5, 1.0])  # пауза растёт

    def test_gives_up_after_all_attempts(self):
        gibdd = FakeGibdd([(500, {"detail": "сбой"})]); self.addCleanup(gibdd.close)
        with self.assertRaises(DeliveryError) as ctx:
            self.client(gibdd.url, attempts=3).send_detection(EVENT)
        self.assertNotIsInstance(ctx.exception, DeliveryRejected)
        self.assertEqual(len(gibdd.requests), 3)

    def test_client_error_is_not_retried(self):
        for status in (401, 422):
            gibdd = FakeGibdd([(status, {"detail": "нельзя"})]); self.addCleanup(gibdd.close)
            with self.assertRaises(DeliveryRejected) as ctx:
                self.client(gibdd.url, attempts=3).send_detection(EVENT)
            self.assertEqual((ctx.exception.status, ctx.exception.detail), (status, "нельзя"))
            self.assertEqual(len(gibdd.requests), 1)

    def test_unreachable_service(self):
        c = self.client(f"http://127.0.0.1:{free_port()}", attempts=2)
        with self.assertRaises(DeliveryError):
            c.send_detection(EVENT)
        self.assertEqual(c.sleeps, [0.5])


class EmitterTests(unittest.TestCase):
    def setUp(self):
        self.gibdd = FakeGibdd(); self.addCleanup(self.gibdd.close)
        self.watchlist = Watchlist()
        self.client = GibddClient(self.gibdd.url, "tok", timeout=2, attempts=1)

    def emitter(self, cameras=None, interval=60):
        return Emitter(cameras or [camera("CAM-01"), camera("CAM-02")], self.watchlist, self.client, interval, rng=random.Random(1))

    def test_nothing_is_sent_for_empty_watchlist(self):
        self.assertIsNone(self.emitter().tick())
        self.assertEqual(self.gibdd.requests, [])

    def test_sends_only_plates_from_the_watchlist(self):
        self.watchlist.replace(["А1", "Б2"])
        e = self.emitter()
        for _ in range(10):
            e.tick()
        self.assertEqual(len(self.gibdd.requests), 10)
        self.assertTrue({r["body"]["plate"] for r in self.gibdd.requests} <= {"А1", "Б2"})

    def test_inactive_cameras_are_never_used(self):
        self.watchlist.replace(["А1"])
        e = self.emitter([camera("CAM-01", active=False), camera("CAM-02")])
        for _ in range(10):
            e.tick()
        self.assertEqual({r["body"]["camera_code"] for r in self.gibdd.requests}, {"CAM-02"})

    def test_no_active_cameras_means_no_events(self):
        self.watchlist.replace(["А1"])
        self.assertIsNone(self.emitter([camera("CAM-01", active=False)]).tick())

    def test_event_shape(self):
        event = build_event("А1", camera("CAM-08"))
        self.assertEqual(set(event), {"event_id", "plate", "camera_code", "detected_at"})
        self.assertEqual(len(event["event_id"]), 32)
        self.assertIsNotNone(datetime.fromisoformat(event["detected_at"]).tzinfo)  # время с поясом
        self.assertNotEqual(event["event_id"], build_event("А1", camera("CAM-08"))["event_id"])

    def test_failed_delivery_does_not_raise(self):
        self.watchlist.replace(["А1"])
        self.gibdd.responses = [(500, {"detail": "сбой"})]
        self.assertIsNone(self.emitter().tick())

    def test_detect_with_given_camera(self):
        result = self.emitter().detect(" а1 ", "CAM-02")
        self.assertEqual(result["event"]["plate"], "А1")
        self.assertEqual(result["event"]["camera_code"], "CAM-02")
        self.assertEqual(result["gibdd_response"]["status"], "accepted")

    def test_detect_unknown_or_inactive_camera(self):
        e = self.emitter([camera("CAM-01"), camera("CAM-02", active=False)])
        for code in ("CAM-99", "CAM-02"):
            with self.assertRaises(UnknownCamera):
                e.detect("А1", code)
        self.assertEqual(self.gibdd.requests, [])

    def test_detect_without_camera_picks_an_active_one(self):
        e = self.emitter([camera("CAM-01", active=False), camera("CAM-02")])
        self.assertEqual(e.detect("А1")["event"]["camera_code"], "CAM-02")

    def test_run_loop_emits_periodically_and_stops(self):
        self.watchlist.replace(["А1"])
        e = self.emitter(interval=0.05)
        stop = threading.Event()
        t = threading.Thread(target=e.run, args=(stop,), daemon=True); t.start()
        self.assertTrue(wait_until(lambda: len(self.gibdd.requests) >= 3))
        stop.set(); t.join(timeout=2)
        self.assertFalse(t.is_alive())


if __name__ == "__main__":
    unittest.main()
