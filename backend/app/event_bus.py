from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from .contracts import FlightEvent, VisionEvent


class EventOverflow(RuntimeError):
    pass


class EventSubscription:
    def __init__(self, queue: asyncio.Queue[FlightEvent]) -> None:
        self._queue = queue
        self._closed = False

    async def get(self) -> FlightEvent:
        if self._closed:
            raise asyncio.CancelledError
        return await self._queue.get()

    def __aiter__(self) -> AsyncIterator[FlightEvent]:
        return self

    async def __anext__(self) -> FlightEvent:
        try:
            return await self.get()
        except asyncio.CancelledError as exc:
            raise StopAsyncIteration from exc

    async def close(self) -> None:
        self._closed = True


class EventBus:
    def __init__(self, max_queue_size: int = 128) -> None:
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
        self._max_queue_size = max_queue_size
        self._subscriptions: set[EventSubscription] = set()

    def subscribe(self) -> EventSubscription:
        subscription = EventSubscription(asyncio.Queue(self._max_queue_size))
        self._subscriptions.add(subscription)
        return subscription

    async def publish(self, event: FlightEvent) -> None:
        for subscription in tuple(self._subscriptions):
            if subscription._closed:
                self._subscriptions.discard(subscription)
                continue
            queue = subscription._queue
            if queue.full():
                self._discard_oldest_vision(queue)
                if queue.full():
                    await subscription.close()
                    self._subscriptions.discard(subscription)
                    raise EventOverflow("critical event subscriber queue is full")
            queue.put_nowait(event)

    @staticmethod
    def _discard_oldest_vision(queue: asyncio.Queue[FlightEvent]) -> None:
        items: list[FlightEvent] = []
        discarded = False
        while not queue.empty():
            item = queue.get_nowait()
            if not discarded and isinstance(item, VisionEvent):
                discarded = True
                continue
            items.append(item)
        for item in items:
            queue.put_nowait(item)
