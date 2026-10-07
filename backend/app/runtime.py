"""Небольшой общий модуль, чтобы синхронный поток симулятора мог
достучаться до event loop FastAPI и разослать сообщение через WebSocket."""
import asyncio
from typing import Optional

main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop):
    global main_loop
    main_loop = loop
