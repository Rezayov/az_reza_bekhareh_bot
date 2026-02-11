from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 0.5) -> None:
        super().__init__()
        self.rate = rate
        self._locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_call: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, object]], asyncio.Future],
        event: TelegramObject,
        data: Dict[str, object],
    ) -> object:
        user_id = self._extract_user_id(event)
        if user_id is None:
            return await handler(event, data)

        async with self._locks[user_id]:
            now = time.monotonic()
            last = self._last_call.get(user_id, 0.0)
            delta = now - last
            if delta < self.rate:
                await asyncio.sleep(self.rate - delta)
            self._last_call[user_id] = time.monotonic()
        return await handler(event, data)

    @staticmethod
    def _extract_user_id(event: TelegramObject) -> Optional[int]:
        if isinstance(event, Message) and event.from_user:
            return event.from_user.id
        return None

