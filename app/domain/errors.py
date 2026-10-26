"""Erreurs du domaine.

Elles expriment des règles métier violées. Elles ne connaissent PAS HTTP :
c'est l'adaptateur entrant qui les traduit en codes de statut.
"""
from dataclasses import asdict, dataclass


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str, details: list | dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidQuantity(DomainError):
    code = "invalid_quantity"


class EmptyOrder(DomainError):
    code = "empty_order"


class ProductNotFound(DomainError):
    code = "product_not_found"


class OrderNotFound(DomainError):
    code = "order_not_found"


@dataclass(frozen=True)
class StockShortage:
    product_id: int
    product_name: str
    requested: int
    available: int


class InsufficientStock(DomainError):
    code = "insufficient_stock"

    def __init__(self, shortages: list[StockShortage]):
        super().__init__("Stock insuffisant.", [asdict(s) for s in shortages])
        self.shortages = shortages


class OrderAlreadyCancelled(DomainError):
    code = "order_already_cancelled"


class InvalidStatusTransition(DomainError):
    code = "invalid_status_transition"
