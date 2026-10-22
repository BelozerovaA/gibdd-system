import asyncio
import importlib.util
import os
import sys
import types
import unittest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANAGER_PY = os.path.join(BACKEND_DIR, "app", "websocket", "manager.py")


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


class FakeWebSocket:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("соединение закрыто")
        self.sent.append(message)


class ConnectionManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = load_manager_module().ConnectionManager()

    def send(self, user_id, message):
        return asyncio.run(self.manager.send_personal_message(user_id, message))

    def test_message_is_delivered_to_open_connection(self):
        ws = FakeWebSocket()
        self.manager.active_connections[2] = ws
        self.assertTrue(self.send(2, {"type": "detection"}))
        self.assertEqual(ws.sent, [{"type": "detection"}])

    def test_no_connection_means_not_delivered(self):
        self.assertFalse(self.send(2, {"type": "detection"}))

    def test_failed_send_drops_connection_and_reports_false(self):
        self.manager.active_connections[2] = FakeWebSocket(fail=True)
        self.assertFalse(self.send(2, {"type": "detection"}))
        self.assertNotIn(2, self.manager.active_connections)

    def test_message_goes_only_to_the_addressee(self):
        mine, other = FakeWebSocket(), FakeWebSocket()
        self.manager.active_connections.update({2: mine, 3: other})
        self.send(2, {"x": 1})
        self.assertEqual(len(mine.sent), 1)
        self.assertEqual(other.sent, [])

    def test_closing_old_connection_keeps_the_new_one(self):
        old, new = FakeWebSocket(), FakeWebSocket()
        self.manager.active_connections[2] = new
        self.manager.disconnect(2, old)
        self.assertIs(self.manager.active_connections.get(2), new)
        self.manager.disconnect(2, new)
        self.assertNotIn(2, self.manager.active_connections)

    def test_disconnect_of_unknown_user_is_harmless(self):
        self.manager.disconnect(42, FakeWebSocket())


if __name__ == "__main__":
    unittest.main()
