import asyncio
import contextlib
import time
from collections.abc import Callable

from polymarket._internal.ws.heartbeat import SendText

CLOB_HEARTBEAT_INTERVAL_S = 10.0
CLOB_HEARTBEAT_STALE_S = 30.0
_PING = "PING"
_PONG = "PONG"


class ClobWebSocketHeartbeat:
    """Application-level PING/PONG heartbeat for the CLOB stream."""

    def __init__(
        self,
        *,
        interval_s: float = CLOB_HEARTBEAT_INTERVAL_S,
        stale_s: float = CLOB_HEARTBEAT_STALE_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if interval_s <= 0:
            raise ValueError("interval_s must be positive")
        if stale_s <= 0:
            raise ValueError("stale_s must be positive")
        self._interval_s = interval_s
        self._stale_s = stale_s
        self._clock = clock
        self._timer: asyncio.Task[None] | None = None
        self._last_pong: float = 0.0

    async def start(self, send: SendText) -> None:
        await self.stop()
        self._last_pong = self._clock()
        self._timer = asyncio.create_task(self._tick(send))

    async def stop(self) -> None:
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await timer

    def handle(self, message: str) -> bool:
        if message != _PONG:
            return False
        self._last_pong = self._clock()
        return True

    def is_stale(self, now: float) -> bool:
        return now - self._last_pong > self._stale_s

    async def _tick(self, send: SendText) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval_s)
                await send(_PING)
        except asyncio.CancelledError:
            return
