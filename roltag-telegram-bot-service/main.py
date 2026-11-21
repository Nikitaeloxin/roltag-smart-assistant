import asyncio
import logging
import uuid

from app.core.config import settings
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import ErrorEvent

from app.models.models import AskRequest
from app.clients.rag_client import RagClientError, rag_client

from app.core.logging import new_request_id, setup_logging

setup_logging()

logger = logging.getLogger("app.telegram")

TELEGRAM_BOT_TOKEN = settings.telegram_bot_token

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the environment variables.")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_command_handler(message):
    await message.answer("Hello! I'm your bot. How can I assist you today?")

async def _typing_loop(chat_id):
    while True:
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(4)

@dp.message()
async def echo_message_handler(message):
    request_id = new_request_id()
    typing_task = asyncio.create_task(_typing_loop(message.chat.id))

    request = AskRequest(question=message.text)
    try:
        response = await rag_client.get_answer(request, request_id=request_id)
    except RagClientError as e:
        logger.exception("rag_client failed", extra={"request_id": request_id})
        await message.answer("Sorry, I couldn't get an answer right now. Please try again shortly.")
        return
    finally:
        typing_task.cancel()

    answer = response.answer
    await message.answer(f"Answer: {answer}")

@dp.error()
async def global_error_handler(event: ErrorEvent):
    logger.exception(
        "Unhandled error in update processing",
        exc_info=event.exception,
    )
    if event.update.message:
        await event.update.message.answer(
            "Sorry, something went wrong. Please try again shortly."
        )

async def main():
    try:
        print("Bot is starting...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
     asyncio.run(main())
