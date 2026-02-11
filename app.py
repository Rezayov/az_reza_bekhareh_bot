from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from fastapi import FastAPI

from .config import settings
from .db import init_db
from .handlers import admin, auth, browse, dispute, payment, profile, rating, reserve, sell, start
from .middlewares.throttling import ThrottlingMiddleware
from .scheduler.jobs import setup_scheduler


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ThrottlingMiddleware())

    dp.include_router(start.router)
    dp.include_router(auth.router)
    dp.include_router(profile.router)
    dp.include_router(sell.router)
    dp.include_router(browse.router)
    dp.include_router(reserve.router)
    dp.include_router(payment.router)
    dp.include_router(rating.router)
    dp.include_router(dispute.router)
    dp.include_router(admin.router)

    return dp


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    scheduler = setup_scheduler(bot)
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)


async def main() -> None:
    setup_logging()
    await init_db()
    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = build_dispatcher()

    if settings.webhook_url:
        logging.info("حالت وبهوک فعال است. لطفاً با uvicorn برنامه FastAPI را اجرا کن.")
        return
    await _run_polling(bot, dp)


def create_fastapi_app(bot: Bot, dp: Dispatcher) -> FastAPI:
    scheduler = setup_scheduler(bot)
    app = FastAPI()

    @app.on_event("startup")
    async def on_startup() -> None:
        await init_db()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        scheduler.shutdown(wait=False)
        await bot.session.close()

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    setup_application(app, webhook_handler, path="/webhook")
    return app


if __name__ == "__main__":
    asyncio.run(main())
