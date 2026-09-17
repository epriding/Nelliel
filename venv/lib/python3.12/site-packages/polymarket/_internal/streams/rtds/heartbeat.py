import asyncio
import contextlib
import time
from collections.abc import Callable

from polymarket._internal.ws.heartbeat import SendText

RTDS_HEARTBEAT_INTERVAL_S = 5.0
RTDS_HEARTBEAT_STALE_S = 10 * 60.0
_PING = "PING"


class RtdsWebSocketHeartbeat:
    def __init__(
        self,
        *,
        interval_s: float = RTDS_HEARTBEAT_INTERVAL_S,
        stale_s: float = RTDS_HEARTBEAT_STALE_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if interval_s <= 0:
            raise ValueError("interval_s must be positive")
        if stale_s <= 0:
            raise ValueError("stale_s must be positive")
        self._interval_s = interval_s
        self._stale_s = stale_s
        self._clock = clock
        self._send: SendText | None = None
        self._last_message: float = 0.0
        self._timer: asyncio.Task[None] | None = None

    async def start(self, send: SendText) -> None:
        await self.stop()
        self._send = send
        self._last_message = self._clock()
        self._timer = asyncio.create_task(self._tick(send))

    async def stop(self) -> None:
        self._send = None
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await timer

    def handle(self, message: str) -> bool:  # noqa: ARG002
        self._last_message = self._clock()
        return False

    def is_stale(self, now: float) -> bool:
        return now - self._last_message > self._stale_s

    async def _tick(self, send: SendText) -> None:
        try:
            while True:
                await asyncio.sleep(self._interval_s)
                await send(_PING)
        except asyncio.CancelledError:
            return
