from aiogram import BaseMiddleware
from states import users
from logger import logger
from states import ProfileSetup


class CheckCommandMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id

        allowed_commands = ['/set_profile', '/start', '/help']

        if (
                (event.text and any(event.text.startswith(cmd) for cmd in allowed_commands)) or
                isinstance(data.get('state'), ProfileSetup) or data.get('raw_state') is not None
                and data['raw_state'].startswith('ProfileSetup')
           ):

            return await handler(event, data)

        if user_id not in users:
            await event.answer("Set up your profile for using bot")
            return

        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        logger.info("Message from user {} with text: {}", event.from_user.id, event.text)
        return await handler(event, data)