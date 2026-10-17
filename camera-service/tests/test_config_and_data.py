"""Настройки, список камер и список розыска."""
import json
import os
import tempfile
import threading
import unittest

from app.cameras import find_camera, load_cameras
from app.config import ConfigError, load_settings
from app.watchlist import Watchlist, normalize_plate

PACKAGED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "cameras.json")


class SettingsTests(unittest.TestCase):
    def test_defaults(self):
        s = load_settings({})
        self.assertEqual(s.gibdd_url, "http://localhost:8000")
        self.assertEqual((s.interval_seconds, s.port, s.delivery_attempts), (60.0, 9000, 3))
        self.assertTrue(s.manual_detections_enabled)
        self.assertEqual(s.service_token, "")

    def test_values_from_environment(self):
        s = load_settings({"GIBDD_URL": "http://backend:8000/", "SERVICE_TOKEN": " tok ", "CAMERA_INTERVAL_SECONDS": "10",
                           "PORT": "9100", "DELIVERY_ATTEMPTS": "5", "ENABLE_MANUAL_DETECTIONS": "false"})
        self.assertEqual(s.gibdd_url, "http://backend:8000")  # косая черта в конце убирается
        self.assertEqual((s.service_token, s.interval_seconds, s.port, s.delivery_attempts), ("tok", 10.0, 9100, 5))
        self.assertFalse(s.manual_detections_enabled)

    def test_invalid_values_are_reported_clearly(self):
        for env in ({"CAMERA_INTERVAL_SECONDS": "abc"}, {"CAMERA_INTERVAL_SECONDS": "0"}, {"PORT": "x"},
                    {"DELIVERY_ATTEMPTS": "0"}, {"ENABLE_MANUAL_DETECTIONS": "может быть"}):
            with self.assertRaises(ConfigError, msg=str(env)):
                load_settings(env)


class CamerasTests(unittest.TestCase):
    def test_packaged_file_has_fifteen_unique_cameras(self):
        cameras = load_cameras(PACKAGED)
        self.assertEqual(len(cameras), 15)
        self.assertEqual(len({c.code for c in cameras}), 15)
        self.assertEqual(find_camera(cameras, "CAM-08").address, "ул. Московская 106/1")
        self.assertTrue(all(c.active for c in cameras))

    def test_unknown_code(self):
        self.assertIsNone(find_camera(load_cameras(PACKAGED), "CAM-99"))

    def write(self, data):
        path = os.path.join(self._tmp.name, "c.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_broken_files_are_rejected(self):
        good = {"code": "A", "address": "ул. А", "latitude": 1, "longitude": 2}
        for data in ([], {"cameras": []}, {"cameras": [{"code": "A"}]},
                     {"cameras": [good, good]}, {"cameras": [dict(good, code="")]}):
            with self.assertRaises(ValueError, msg=str(data)):
                load_cameras(self.write(data))


class WatchlistTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_plate(" а123 вк43 "), "А123ВК43")

    def test_replace_dedupes_normalizes_and_sorts(self):
        w = Watchlist()
        self.assertEqual(w.replace(["е456км43", "А123ВК43", " а123 вк43", ""]), 2)
        self.assertEqual(w.snapshot(), ["А123ВК43", "Е456КМ43"])

    def test_replace_is_a_full_snapshot(self):
        w = Watchlist()
        w.replace(["А1", "Б2"])
        w.replace(["В3"])
        self.assertEqual(w.snapshot(), ["В3"])
        w.replace([])
        self.assertEqual(len(w), 0)

    def test_snapshot_is_a_copy(self):
        w = Watchlist()
        w.replace(["А1"])
        w.snapshot().append("Х")
        self.assertEqual(w.snapshot(), ["А1"])

    def test_parallel_use(self):
        w = Watchlist()
        def work(n):
            for i in range(200):
                w.replace([f"А{n}{i}"]); w.snapshot()
        ts = [threading.Thread(target=work, args=(n,)) for n in range(4)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(w), 1)


if __name__ == "__main__":
    unittest.main()
