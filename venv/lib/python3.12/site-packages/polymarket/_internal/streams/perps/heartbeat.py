import asyncio
import contextlib
import json
import time
from collections.abc import Callable

from polymarket._internal.ws.heartbeat import SendText

PERPS_HEARTBEAT_INTERVAL_S = 25.0
PERPS_HEARTBEAT_STALE_S = 65.0

_PING_FRAME = json.dumps({"id": 0, "req": "post", "op": {"type": "ping"}}, separators=(",", ":"))


class PerpsWebSocketHeartbeat:
    """Application-level ping heartbeat for Perps WebSocket connections.

    Any inbound message counts as liveness; the connection is stale when no
    message has arrived within the stale window.
    """

    def __init__(
        self,
        *,
        interval_s: float = PERPS_HEARTBEAT_INTERVAL_S,
        stale_s: float = PERPS_HEARTBEAT_STALE_S,
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
        self._last_message: float = 0.0

    async def start(self, send: SendText) -> None:
        await self.stop()
        self._last_message = self._clock()
        self._timer = asyncio.create_task(self._tick(send))

    async def stop(self) -> None:
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await timer

    def handle(self, message: str) -> bool:
        self._last_message = self._clock()
        return False

    def is_stale(self, now: float) -> bool:
        return now - self._last_message > self._stale_s

    async def _tick(self, send: SendText) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval_s)
                await send(_PING_FRAME)
        except asyncio.CancelledError:
            return
