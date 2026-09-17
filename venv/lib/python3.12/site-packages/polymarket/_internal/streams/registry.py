# pyright: reportPrivateUsage=false
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar

from polymarket._internal.streams.handle import AsyncSubscriptionHandle

Sub = TypeVar("Sub")
Event = TypeVar("Event")
State = TypeVar("State")

Matcher = Callable[[Event], bool]
DeriveState = Callable[[Iterable[Sub]], State]


@dataclass(slots=True)
class _Entry(Generic[Sub, Event]):
    sub: Sub
    matcher: Matcher[Event]
    handle: AsyncSubscriptionHandle[Event]


class SubscriptionRegistry(Generic[Sub, Event, State]):
    """Multiplexes many subscriptions onto one derived server state."""

    def __init__(
        self,
        *,
        derive_state: DeriveState[Sub, State],
        logger: logging.Logger | None = None,
    ) -> None:
        self._derive_state = derive_state
        self._entries: list[_Entry[Sub, Event]] = []
        self._logger = logger or logging.getLogger("polymarket.streams.registry")

    @property
    def is_empty(self) -> bool:
        return not self._entries

    def server_state(self) -> State:
        return self._derive_state(entry.sub for entry in self._entries)

    def add(
        self,
        *,
        sub: Sub,
        matcher: Matcher[Event],
        handle: AsyncSubscriptionHandle[Event],
    ) -> None:
        self._entries.append(_Entry(sub=sub, matcher=matcher, handle=handle))

    def remove_handle(self, handle: AsyncSubscriptionHandle[Event]) -> bool:
        for i, entry in enumerate(self._entries):
            if entry.handle is handle:
                del self._entries[i]
                return True
        return False

    def dispatch(self, event: Event) -> None:
        for entry in self._entries:
            try:
                matched = entry.matcher(event)
            except Exception:
                self._logger.exception("matcher raised; event dropped for this entry")
                continue
            if matched:
                entry.handle._push(event)

    def end_all(self, error: BaseException | None = None) -> None:
        for entry in self._entries:
            entry.handle._end(error)
        self._entries.clear()
