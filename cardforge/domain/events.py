"""Domain event dispatch."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Awaitable, Callable, DefaultDict, Iterable, Protocol


class EventPayload(Protocol):
    """Marker protocol for event payloads."""


EventListener = Callable[[EventPayload], Awaitable[None]]


@dataclass(slots=True)
class Event:
    name: str
    payload: EventPayload


class EventBus:
    """Simple async pub-sub used by the framework."""

    def __init__(self) -> None:
        self._listeners: DefaultDict[str, list[EventListener]] = defaultdict(list)

    def subscribe(self, event_name: str, listener: EventListener) -> None:
        self._listeners[event_name].append(listener)

    async def publish(self, event_name: str, payload: EventPayload) -> None:
        for listener in list(self._listeners.get(event_name, ())):
            await listener(payload)

    def clear(self) -> None:
        self._listeners.clear()

    def listeners(self, event_name: str) -> Iterable[EventListener]:
        return tuple(self._listeners.get(event_name, ()))
