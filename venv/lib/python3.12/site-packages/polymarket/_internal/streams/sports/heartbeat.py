import asyncio
import contextlib
import time
from collections.abc import Callable

from polymarket._internal.ws.heartbeat import SendText

SPORTS_HEARTBEAT_STALE_S = 30.0
_PING = "ping"
_PONG = "pong"


class SportsWebSocketHeartbeat:
    """Server-initiated heartbeat for the Sports stream.

    The server sends raw text ``"ping"`` (lowercase). The client must reply
    with raw text ``"pong"`` (lowercase). The connection is considered stale
    if no ping has been received within ``stale_s`` seconds.
    """

    def __init__(
        self,
        *,
        stale_s: float = SPORTS_HEARTBEAT_STALE_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if stale_s <= 0:
            raise ValueError("stale_s must be positive")
        self._stale_s = stale_s
        self._clock = clock
        self._send: SendText | None = None
        self._last_ping: float = 0.0
        self._pending_pongs: set[asyncio.Task[bool]] = set()

    async def start(self, send: SendText) -> None:
        self._send = send
        self._last_ping = self._clock()

    async def stop(self) -> None:
        self._send = None
        # Cancel before awaiting: a stuck send (e.g. a half-dead socket) must
        # not block shutdown. With cancellation, gather returns promptly.
        pending = list(self._pending_pongs)
        self._pending_pongs.clear()
        for task in pending:
            if not task.done():
                task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    def handle(self, message: str) -> bool:
        if message != _PING:
            return False
        self._last_ping = self._clock()
        send = self._send
        if send is not None:
            task = asyncio.create_task(_send_pong(send))
            self._pending_pongs.add(task)
            task.add_done_callback(self._pending_pongs.discard)
        return True

    def is_stale(self, now: float) -> bool:
        return now - self._last_ping > self._stale_s


async def _send_pong(send: SendText) -> bool:
    with contextlib.suppress(Exception):
        return await send(_PONG)
    return False
