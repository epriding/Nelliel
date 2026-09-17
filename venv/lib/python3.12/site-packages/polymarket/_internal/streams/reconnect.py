import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from polymarket._internal.ws.backoff import (
    DEFAULT_BASE_DELAY_S,
    DEFAULT_MAX_DELAY_S,
    jittered_backoff,
)


class ReconnectScheduler:
    def __init__(
        self,
        *,
        base_s: float = DEFAULT_BASE_DELAY_S,
        max_s: float = DEFAULT_MAX_DELAY_S,
        logger: logging.Logger | None = None,
    ) -> None:
        self._base_s = base_s
        self._max_s = max_s
        self._logger = logger or logging.getLogger("polymarket.streams.reconnect")
        self._attempt = 0
        self._timer: asyncio.Task[None] | None = None
        self._stopped = False

    @property
    def attempt(self) -> int:
        return self._attempt

    @property
    def is_pending(self) -> bool:
        return self._timer is not None

    def schedule(
        self,
        *,
        reconnect: Callable[[], Awaitable[None]],
        should_reconnect: Callable[[], bool],
    ) -> None:
        if self._stopped or self._timer is not None or not should_reconnect():
            return
        delay = jittered_backoff(self._attempt, base_s=self._base_s, max_s=self._max_s)
        self._attempt += 1
        self._timer = asyncio.create_task(self._run(delay, reconnect, should_reconnect))

    async def _run(
        self,
        delay: float,
        reconnect: Callable[[], Awaitable[None]],
        should_reconnect: Callable[[], bool],
    ) -> None:
        me = asyncio.current_task()
        try:
            await asyncio.sleep(delay)
            if self._stopped or not should_reconnect():
                return
            # Clear only if we still own the slot; reconnect() may re-schedule.
            if self._timer is me:
                self._timer = None
            await reconnect()
        except asyncio.CancelledError:
            return
        except Exception:
            self._logger.exception("reconnect callback raised")
        finally:
            if self._timer is me:
                self._timer = None

    def reset(self) -> None:
        self._attempt = 0

    def cancel_pending(self) -> None:
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.cancel()
        self._attempt = 0

    def stop(self) -> None:
        self._stopped = True
        if self._timer is not None:
            self._timer.cancel()

    async def aclose(self) -> None:
        self._stopped = True
        timer = self._timer
        if timer is not None:
            timer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await timer
        self._timer = None
