"""Exceptions raised by CardForge domain services."""


class CardForgeError(RuntimeError):
    """Base class for domain exceptions."""


class CooldownActive(CardForgeError):
    """Raised when player tries to drop before cooldown expires."""

    def __init__(self, seconds_remaining: int) -> None:
        super().__init__(f"Cooldown active for {seconds_remaining} seconds")
        self.seconds_remaining = seconds_remaining


class NoCardsAvailable(CardForgeError):
    """Raised when pack has no eligible cards."""


class PlayerBanned(CardForgeError):
    """Raised when banned player attempts an action."""


class InsufficientCurrency(CardForgeError):
    """Raised when wallet cannot satisfy a spend operation."""
