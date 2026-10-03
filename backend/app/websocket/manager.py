from typing import Dict

from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int, websocket: WebSocket = None):
        current = self.active_connections.get(user_id)
        if current is None:
            return
        if websocket is not None and current is not websocket:
            return
        del self.active_connections[user_id]

    async def send_personal_message(self, user_id: int, message: dict):
        websocket = self.active_connections.get(user_id)
        if websocket is None:
            return
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(user_id, websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections.values()):
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()
