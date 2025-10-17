"""Economy primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping


@dataclass(slots=True)
class Currency:
    code: str
    name: str
    precision: int = 0
    description: str = ""


@dataclass(slots=True)
class Wallet:
    """Mutable wallet representation used by services."""

    balances: Dict[str, int] = field(default_factory=dict)

    def credit(self, currency: str, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot credit negative amount")
        self.balances[currency] = self.balances.get(currency, 0) + amount

    def debit(self, currency: str, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot debit negative amount")
        current = self.balances.get(currency, 0)
        if current < amount:
            raise ValueError(f"Insufficient {currency}: have {current}, need {amount}")
        self.balances[currency] = current - amount

    def merge(self, rewards: Mapping[str, int]) -> None:
        for currency, amount in rewards.items():
            if amount >= 0:
                self.credit(currency, amount)
            else:
                self.debit(currency, -amount)


class CurrencyRegistry:
    """Keeps track of available currencies."""

    def __init__(self) -> None:
        self._currencies: dict[str, Currency] = {}

    def register(self, currency: Currency) -> None:
        if currency.code in self._currencies:
            raise ValueError(f"Currency {currency.code} already registered")
        self._currencies[currency.code] = currency

    def bulk_register(self, currencies: Iterable[Currency]) -> None:
        for currency in currencies:
            self.register(currency)

    def get(self, code: str) -> Currency:
        try:
            return self._currencies[code]
        except KeyError as exc:
            raise KeyError(f"Currency {code} is not configured") from exc

    def ensure_codes(self, codes: Iterable[str]) -> None:
        for code in codes:
            if code not in self._currencies:
                raise KeyError(f"Currency {code} is not configured")

    def all(self) -> Iterable[Currency]:
        return self._currencies.values()
