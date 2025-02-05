import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from logger import logger
from handlers import router
from middlewares import LoggingMiddleware, CheckCommandMiddleware


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(CheckCommandMiddleware())
    dp.include_router(router)

    logger.info("Bot started!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
