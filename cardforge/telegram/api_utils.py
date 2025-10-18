"""Shared helpers to interact with the Telegram Bot API safely."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import CallbackQuery, Message

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


async def safe_api_call(
    label: str,
    func: Callable[P, Awaitable[T]],
    *args: P.args,
    retries: int = 3,
    **kwargs: P.kwargs,
) -> T | None:
    """Execute a Telegram API call, handling transient failures and forbidden errors."""
    attempt = 0
    while True:
        try:
            return await func(*args, **kwargs)
        except TelegramRetryAfter as exc:
            attempt += 1
            if attempt >= retries:
                logger.warning(
                    "Telegram call '%s' exceeded retry limit (%s attempts, retry_after=%s).",
                    label,
                    attempt,
                    getattr(exc, "retry_after", None),
                )
                return None
            delay = float(getattr(exc, "retry_after", 0) or 1.0)
            logger.info(
                "Telegram call '%s' hit rate limit; sleeping for %.1f s (attempt %s/%s).",
                label,
                delay,
                attempt,
                retries,
            )
            await asyncio.sleep(delay)
        except TelegramForbiddenError:
            logger.info(
                "Telegram call '%s' forbidden (likely blocked by the user).",
                label,
            )
            return None
        except TelegramBadRequest as exc:
            message = str(exc)
            if "message is not modified" in message.lower():
                logger.debug(
                    "Telegram call '%s' skipped: message content unchanged.",
                    label,
                )
            else:
                logger.warning("Telegram call '%s' bad request: %s", label, message)
            return None
        except TelegramAPIError as exc:
            logger.error("Telegram call '%s' failed: %s", label, exc, exc_info=True)
            return None
        except Exception:  # pragma: no cover - defensive safeguard
            logger.exception("Unexpected error during Telegram call '%s'.", label)
            return None


async def safe_message_answer(message: Message | None, text: str, **kwargs) -> bool:
    """Send a message.answer call while handling expected Telegram errors."""
    if not message:
        return False
    return (await safe_api_call("message.answer", message.answer, text, **kwargs)) is not None


async def safe_message_edit_text(
    message: Message | None,
    text: str,
    **kwargs,
) -> bool:
    """Safely edit an existing message text."""
    if not message:
        return False
    return (
        await safe_api_call("message.edit_text", message.edit_text, text, **kwargs)
    ) is not None


async def safe_message_answer_dice(
    message: Message | None,
    *,
    emoji: str = "🎲",
) -> Message | None:
    """Send a dice message safely and return the Telegram message if successful."""
    if not message:
        return None
    return await safe_api_call("message.answer_dice", message.answer_dice, emoji=emoji)


async def safe_callback_answer(
    callback: CallbackQuery | None,
    text: str | None = None,
    **kwargs,
) -> bool:
    """Safely acknowledge a callback query."""
    if not callback:
        return False
    params = dict(kwargs)
    if text is not None:
        params["text"] = text
    return (await safe_api_call("callback.answer", callback.answer, **params)) is not None
