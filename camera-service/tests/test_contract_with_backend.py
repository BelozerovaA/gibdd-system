"""Согласованность двух отдельных сервисов: сервис камер и сервис ГИБДД.

Они обмениваются данными по протоколу и ничего не импортируют друг у друга, поэтому
рассинхронизацию (переименовали поле или адрес только с одной стороны) не поймает ни
один из их собственных тестов. Этот тест читает исходники обеих сторон и сравнивает.

Тест пропускается, если рядом нет папки backend (например, внутри Docker-образа).
"""
import ast
import json
import os
import re
import unittest

from app.cameras import load_cameras
from app.emitter import build_event

SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(os.path.dirname(SERVICE_DIR), "backend")
CAMERAS_JSON = os.path.join(SERVICE_DIR, "app", "cameras.json")


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


@unittest.skipUnless(os.path.isdir(BACKEND_DIR), "папка backend не найдена")
class ContractTests(unittest.TestCase):
    def test_cameras_match_the_gibdd_database_seed(self):
        tree = ast.parse(read(BACKEND_DIR, "seed.py"))
        seed = next(ast.literal_eval(n.value) for n in ast.walk(tree)
                    if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "CAMERAS" for t in n.targets))
        seed_by_code = {code: (address, lat, lon) for code, address, lat, lon, _type, _speed in seed}
        service_by_code = {c.code: (c.address, c.latitude, c.longitude) for c in load_cameras(CAMERAS_JSON)}
        self.assertEqual(service_by_code, seed_by_code,
                         "Камеры в camera-service/app/cameras.json и в backend/seed.py разошлись")

    def test_event_fields_match_backend_schema(self):
        tree = ast.parse(read(BACKEND_DIR, "app", "schemas.py"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "CameraEvent")
        schema_fields = {n.target.id for n in cls.body if isinstance(n, ast.AnnAssign)}
        camera = load_cameras(CAMERAS_JSON)[0]
        self.assertEqual(set(build_event("А1", camera)), schema_fields)

    def test_event_endpoint_path_matches(self):
        main = read(BACKEND_DIR, "app", "main.py")
        route = read(BACKEND_DIR, "app", "routes", "camera_events.py")
        prefix = re.search(r'camera_events_routes\.router,\s*prefix="([^"]+)"', main).group(1)
        path = re.search(r'@router\.post\("([^"]+)"', route).group(1)
        client = read(SERVICE_DIR, "app", "gibdd_client.py")
        self.assertIn(f'f"{{self.base_url}}{prefix}{path}"', client)

    def test_watchlist_path_matches(self):
        publisher = read(BACKEND_DIR, "app", "services", "camera_client.py")
        server = read(SERVICE_DIR, "app", "server.py")
        backend_path = re.search(r"/v1/watchlist", publisher)
        self.assertIsNotNone(backend_path)
        self.assertIn('("PUT", "/v1/watchlist")', server)
        self.assertIn('method="PUT"', publisher)

    def test_token_header_is_the_same_on_both_sides(self):
        self.assertIn('"X-Service-Token"', read(BACKEND_DIR, "app", "services", "camera_client.py"))
        self.assertIn('"X-Service-Token"', read(SERVICE_DIR, "app", "gibdd_client.py"))
        self.assertIn('"X-Service-Token"', read(SERVICE_DIR, "app", "server.py"))
        # FastAPI превращает параметр x_service_token в заголовок X-Service-Token
        self.assertIn("x_service_token", read(BACKEND_DIR, "app", "service_auth.py"))

    def test_ignore_reasons_are_documented_in_the_route(self):
        rules = read(BACKEND_DIR, "app", "services", "detection_rules.py")
        route = read(BACKEND_DIR, "app", "routes", "camera_events.py")
        for reason in re.findall(r'IGNORE_\w+ = "(\w+)"', rules):
            self.assertIn(reason, route, f"Причина {reason} не описана в docstring маршрута")

    def test_websocket_payload_keys_match_what_clients_read(self):
        detections = read(BACKEND_DIR, "app", "services", "detections.py")
        keys = set(re.findall(r'"(\w+)":', detections[detections.index("payload={"):]))
        # поля, которые читают web и мобильное приложение
        self.assertTrue({"alert_id", "plate", "camera_number", "address", "date", "time"} <= keys)


if __name__ == "__main__":
    unittest.main()
