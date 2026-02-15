import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from tgbot.handlers import router
from tgbot.runtime import bot


dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)


async def main():
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
