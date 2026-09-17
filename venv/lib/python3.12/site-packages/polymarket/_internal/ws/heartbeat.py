from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

SendText = Callable[[str], Awaitable[bool]]


@runtime_checkable
class Heartbeat(Protocol):
    async def start(self, send: SendText) -> None: ...
    async def stop(self) -> None: ...
    def handle(self, message: str) -> bool: ...
    def is_stale(self, now: float) -> bool: ...


class NoopHeartbeat:
    async def start(self, send: SendText) -> None:  # noqa: ARG002
        return None

    async def stop(self) -> None:
        return None

    def handle(self, message: str) -> bool:
        return False

    def is_stale(self, now: float) -> bool:
        return False
