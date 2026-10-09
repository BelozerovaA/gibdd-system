import asyncio
from typing import Optional

main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop):
    global main_loop
    main_loop = loop
