import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.models import AskResponse
from main import echo_message_handler


def _make_message(text: str = "How often do I replace imaging oil?") -> MagicMock:
    message = MagicMock()
    message.text = text
    message.chat.id = 123
    message.answer = AsyncMock()
    return message


def test_echo_message_handler_replies_with_the_answer():
    fake_response = AskResponse(answer="Replace the imaging oil every 6 months.")
    message = _make_message()

    # Patched where main.py looks it up (main.rag_client), and bot.send_chat_action
    # too -- otherwise the background typing loop would fire a real HTTP call to
    # Telegram's API with our fake token.
    with (
        patch("main.rag_client.get_answer", new=AsyncMock(return_value=fake_response)),
        patch("main.bot.send_chat_action", new=AsyncMock()),
    ):
        asyncio.run(echo_message_handler(message))

    message.answer.assert_called_once_with(
        "Answer: Replace the imaging oil every 6 months."
    )


def test_echo_message_handler_replies_with_fallback_on_rag_client_error():
    from app.clients.rag_client import RagClientError

    message = _make_message()

    with (
        patch(
            "main.rag_client.get_answer",
            new=AsyncMock(side_effect=RagClientError("timeout")),
        ),
        patch("main.bot.send_chat_action", new=AsyncMock()),
    ):
        asyncio.run(echo_message_handler(message))

    message.answer.assert_called_once_with(
        "Sorry, I couldn't get an answer right now. Please try again shortly."
    )
