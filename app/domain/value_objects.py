"""Objets-valeurs : immuables, définis par leur valeur, qui garantissent leurs invariants."""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.errors import InvalidQuantity

_CENTS = Decimal("0.01")


@dataclass(frozen=True)
class Money:
    """Montant en euros, toujours arrondi au centime et jamais négatif. Pas de float."""

    amount: Decimal

    def __post_init__(self):
        amount = Decimal(self.amount).quantize(_CENTS, rounding=ROUND_HALF_UP)
        if amount < 0:
            raise ValueError("Un montant ne peut pas être négatif.")
        object.__setattr__(self, "amount", amount)

    @classmethod
    def zero(cls) -> "Money":
        return cls(Decimal("0"))

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount)

    def __mul__(self, factor: int) -> "Money":
        return Money(self.amount * factor)


@dataclass(frozen=True)
class Quantity:
    """Quantité commandée : un entier STRICTEMENT positif (règle métier du test)."""

    value: int

    def __post_init__(self):
        if isinstance(self.value, bool) or not isinstance(self.value, int) or self.value <= 0:
            raise InvalidQuantity(
                f"La quantité doit être un entier strictement positif (reçu : {self.value}).",
                {"quantity": self.value},
            )

    def __add__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value + other.value)
