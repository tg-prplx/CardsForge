"""Keyboard helpers for CardForge bots."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def card_drop_keyboard(pack_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Roll again", callback_data=f"cardforge:roll:{pack_id}")],
            [InlineKeyboardButton(text="📚 Collection", callback_data="cardforge:collection")],
            [InlineKeyboardButton(text="🎮 Mini-games", callback_data="cardforge:games")],
            [InlineKeyboardButton(text="ℹ️ Help", callback_data="cardforge:help")],
        ]
    )


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Ban user", callback_data="cardforge:admin:ban")],
            [InlineKeyboardButton(text="🎁 Grant rewards", callback_data="cardforge:admin:grant")],
            [InlineKeyboardButton(text="🧾 Audit log", callback_data="cardforge:admin:audit")],
        ]
    )


def welcome_keyboard(default_pack: str | None = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📚 Коллекция", callback_data="cardforge:collection")],
        [InlineKeyboardButton(text="🎮 Мини-игры", callback_data="cardforge:games")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="cardforge:help")],
    ]
    if default_pack:
        buttons.insert(
            0,
            [
                InlineKeyboardButton(
                    text="✨ Получить карту",
                    callback_data=f"cardforge:roll:{default_pack}",
                )
            ],
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
