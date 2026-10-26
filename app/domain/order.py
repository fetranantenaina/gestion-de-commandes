"""Agrégat Order (racine) et ses lignes.

Le cycle de vie du statut est piloté ICI, pas dans les routes ni dans la base :

    PENDING ──validate──▶ VALIDATED
       │                     │
       └────cancel───────────┴──▶ CANCELLED   (état final : pas de seconde annulation)
"""
import enum
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.errors import EmptyOrder, InvalidStatusTransition, OrderAlreadyCancelled
from app.domain.value_objects import Money, Quantity


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"      # En attente
    VALIDATED = "VALIDATED"  # Validée
    CANCELLED = "CANCELLED"  # Annulée


@dataclass(frozen=True)
class OrderLine:
    """Ligne figée : nom et prix sont copiés au moment de la commande (historique stable)."""

    product_id: int
    product_name: str
    quantity: Quantity
    unit_price: Money

    @property
    def total(self) -> Money:
        return self.unit_price * self.quantity.value


@dataclass
class Order:
    lines: list[OrderLine]
    created_at: datetime
    status: OrderStatus = OrderStatus.PENDING
    id: int | None = field(default=None)  # attribué par la persistance

    def __post_init__(self):
        if not self.lines:
            raise EmptyOrder("Une commande doit contenir au moins un produit.")

    @property
    def total(self) -> Money:
        total = Money.zero()
        for line in self.lines:
            total = total + line.total
        return total

    @property
    def product_ids(self) -> list[int]:
        return sorted(line.product_id for line in self.lines)

    def validate(self) -> None:
        if self.status != OrderStatus.PENDING:
            raise InvalidStatusTransition(
                "Seule une commande en attente peut être validée "
                f"(statut actuel : {self.status.value}).",
                {"current_status": self.status.value},
            )
        self.status = OrderStatus.VALIDATED

    def cancel(self) -> None:
        if self.status == OrderStatus.CANCELLED:
            raise OrderAlreadyCancelled(f"La commande {self.id} est déjà annulée.")
        self.status = OrderStatus.CANCELLED
