"""Agrégat Product : il protège l'invariant « le stock n'est jamais négatif »."""
from dataclasses import dataclass

from app.domain.errors import InsufficientStock, StockShortage
from app.domain.value_objects import Money, Quantity


@dataclass
class Product:
    id: int
    name: str
    unit_price: Money
    stock: int

    def __post_init__(self):
        if self.stock < 0:
            raise ValueError("Le stock ne peut pas être négatif.")

    def stock_shortage(self, quantity: Quantity) -> StockShortage | None:
        if quantity.value <= self.stock:
            return None
        return StockShortage(self.id, self.name, quantity.value, self.stock)

    def reserve(self, quantity: Quantity) -> None:
        shortage = self.stock_shortage(quantity)
        if shortage:
            raise InsufficientStock([shortage])
        self.stock -= quantity.value

    def restock(self, quantity: Quantity) -> None:
        self.stock += quantity.value
