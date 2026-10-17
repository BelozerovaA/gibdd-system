"""Общие помощники тестов: поддельный сервис ГИБДД и ожидание условий."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeGibdd:
    """Принимает POST /api/camera-events, запоминает запросы и отвечает заданным образом.

    responses: список ответов (status, body) по очереди; когда список кончается, повторяется последний.
    """

    def __init__(self, responses=None):
        self.requests = []
        self.responses = responses or [(200, {"status": "accepted", "alert_id": 1, "delivered": True})]
        self._lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                with outer._lock:
                    outer.requests.append({"path": self.path, "token": self.headers.get("X-Service-Token"),
                                           "content_type": self.headers.get("Content-Type"), "body": body})
                    index = min(len(outer.requests) - 1, len(outer.responses) - 1)
                    status, payload = outer.responses[index]
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

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
