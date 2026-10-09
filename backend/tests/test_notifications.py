"""Доставка оповещений: колбэк симулятора и менеджер WebSocket.

Проверяется именно связка двух потоков: симулятор работает в обычном потоке,
а WebSocket живёт в event loop. Запускается настоящий loop в отдельном потоке.

Запуск из папки backend:   python -m unittest discover -s tests -v
Тесты не требуют базы данных. Если fastapi не установлен, подставляется заглушка.
"""
import ast
import asyncio
import importlib.util
import os
import sys
import threading
import types
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANAGER_PY = os.path.join(BACKEND_DIR, "app", "websocket", "manager.py")
SIMULATOR_ROUTE_PY = os.path.join(BACKEND_DIR, "app", "routes", "simulator.py")


def load_manager_module():
    try:
        import fastapi  # noqa: F401
    except ImportError:
        stub = types.ModuleType("fastapi")
        stub.WebSocket = object
        sys.modules["fastapi"] = stub
    spec = importlib.util.spec_from_file_location("manager_under_test", MANAGER_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_on_detected():
    """Достаёт функцию _on_detected из routes/simulator.py, не импортируя весь модуль."""
    with open(SIMULATOR_ROUTE_PY, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_on_detected")
    return ast.Module(body=[func], type_ignores=[])


class FakeWebSocket:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("соединение закрыто")
        self.sent.append(message)


class FakeEmail:
    def __init__(self):
        self.calls = []

    def send_alert_async(self, *args):
        self.calls.append(args)


PAYLOAD = {
    "alert_id": 77, "wanted_id": 1, "plate": "А111АА43", "camera_id": 8, "camera_number": 8,
    "address": "ул. Московская 106/1", "latitude": 58.599, "longitude": 49.6547,
    "date": "03.10.2026", "time": "12:00:00",
}


class NotificationTests(unittest.TestCase):
    def setUp(self):
        manager_module = load_manager_module()
        self.manager = manager_module.ConnectionManager()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop_loop)

        self.email = FakeEmail()
        self.runtime = types.SimpleNamespace(main_loop=self.loop)
        namespace = {
            "asyncio": asyncio, "manager": self.manager,
            "runtime": self.runtime, "email_notifier": self.email,
        }
        exec(compile(load_on_detected(), SIMULATOR_ROUTE_PY, "exec"), namespace)
        self.make_callback = namespace["_on_detected"]

    def _stop_loop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=2)
        self.loop.close()

    def connect(self, employee_id, websocket):
        self.manager.active_connections[employee_id] = websocket

    def test_delivered_when_connection_is_open(self):
        ws = FakeWebSocket()
        self.connect(2, ws)
        delivered = self.make_callback(2, "")(dict(PAYLOAD))
        self.assertTrue(delivered)
        self.assertEqual(len(ws.sent), 1)
        self.assertEqual(ws.sent[0]["type"], "detection")
        self.assertEqual(ws.sent[0]["plate"], "А111АА43")
        self.assertEqual(ws.sent[0]["camera_number"], 8)

    def test_not_delivered_without_connection(self):
        self.assertFalse(self.make_callback(2, "")(dict(PAYLOAD)))

    def test_not_delivered_when_send_fails_and_connection_is_dropped(self):
        self.connect(2, FakeWebSocket(fail=True))
        self.assertFalse(self.make_callback(2, "")(dict(PAYLOAD)))
        self.assertNotIn(2, self.manager.active_connections)

    def test_message_goes_only_to_the_addressee(self):
        mine, other = FakeWebSocket(), FakeWebSocket()
        self.connect(2, mine)
        self.connect(3, other)
        self.make_callback(2, "")(dict(PAYLOAD))
        self.assertEqual(len(mine.sent), 1)
        self.assertEqual(other.sent, [])

    def test_email_is_sent_even_when_websocket_is_unavailable(self):
        delivered = self.make_callback(2, "a@example.test")(dict(PAYLOAD))
        self.assertFalse(delivered)
        self.assertEqual(self.email.calls[0][0], "a@example.test")
        self.assertEqual(self.email.calls[0][1], "А111АА43")

    def test_no_email_when_address_is_missing(self):
        self.make_callback(2, "")(dict(PAYLOAD))
        self.assertEqual(self.email.calls, [])

    def test_missing_event_loop_does_not_crash(self):
        self.runtime.main_loop = None
        self.assertFalse(self.make_callback(2, "")(dict(PAYLOAD)))

    def test_closing_old_connection_keeps_the_new_one(self):
        old, new = FakeWebSocket(), FakeWebSocket()
        self.connect(2, new)
        self.manager.disconnect(2, old)  # закрылось старое соединение (перезагрузка страницы)
        self.assertIs(self.manager.active_connections.get(2), new)
        self.manager.disconnect(2, new)
        self.assertNotIn(2, self.manager.active_connections)


if __name__ == "__main__":
    unittest.main()
