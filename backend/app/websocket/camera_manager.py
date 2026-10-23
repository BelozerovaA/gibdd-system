from __future__ import annotations

import asyncio
from typing import Dict, List

from fastapi import WebSocket


class CameraConnectionManager:

    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, camera_code: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            old = self._connections.get(camera_code)
            self._connections[camera_code] = websocket
        if old is not None and old is not websocket:
            try:
                await old.close(code=1000)
            except Exception:
                pass

    async def disconnect(self, camera_code: str, websocket: WebSocket | None = None) -> None:
        async with self._lock:
            current = self._connections.get(camera_code)
            if current is None:
                return
            if websocket is not None and current is not websocket:
                return
            del self._connections[camera_code]

    def connected_codes(self) -> List[str]:
        return list(self._connections.keys())

    def count(self) -> int:
        return len(self._connections)

    async def send_to(self, camera_code: str, message: dict) -> bool:
        ws = self._connections.get(camera_code)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception:
            await self.disconnect(camera_code, ws)
            return False

    async def broadcast(self, message: dict) -> int:
        codes = list(self._connections.keys())
        ok = 0
        for code in codes:
            if await self.send_to(code, message):
                ok += 1
        return ok


camera_manager = CameraConnectionManager()
