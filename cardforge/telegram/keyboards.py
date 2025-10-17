"""Keyboard helpers for CardForge bots."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def card_drop_keyboard(pack_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Roll again", callback_data=f"cardforge:roll:{pack_id}")],
            [InlineKeyboardButton(text="📚 Collection", callback_data="cardforge:collection")],
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
