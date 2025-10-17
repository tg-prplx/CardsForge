"""Automated checks to highlight balancing issues."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from ..app import BotApp


@dataclass(slots=True)
class ChecklistIssue:
    severity: str
    message: str


def run_checklist(app: BotApp) -> list[ChecklistIssue]:
    issues: list[ChecklistIssue] = []
    packs = list(app.cards.catalog.iter_packs())
    if not packs:
        issues.append(ChecklistIssue("error", "Не зарегистрировано ни одного пака."))

    for pack in packs:
        if not pack.cards:
            issues.append(
                ChecklistIssue("error", f"Пак {pack.pack_id} не содержит карт.")
            )

    cards = list(app.cards.catalog.iter_cards())
    if not cards:
        issues.append(ChecklistIssue("error", "Не зарегистрировано ни одной карты."))
    else:
        exp_values = [card.reward.experience for card in cards if card.reward.experience]
        if exp_values and any(exp > mean(exp_values) * 5 for exp in exp_values):
            issues.append(
                ChecklistIssue(
                    "warning",
                    "Некоторые карты дают слишком много опыта по сравнению со средним значением.",
                )
            )

    if not list(app.currencies.registry.all()):
        issues.append(ChecklistIssue("warning", "Не определены валюты."))

    return issues
