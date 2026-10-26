from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.application.ports import UnitOfWorkFactory
from app.domain.order import Order
from app.domain.services import merge_requested_lines, place_order
from app.domain.value_objects import Quantity


@dataclass(frozen=True)
class OrderLineCommand:
    product_id: int
    quantity: int


@dataclass(frozen=True)
class CreateOrderCommand:
    lines: list[OrderLineCommand]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CreateOrder:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Callable[[], datetime] = _utcnow):
        self._uow_factory = uow_factory
        self._clock = clock

    def execute(self, command: CreateOrderCommand) -> Order:
        # Quantity() rejette 0 et les négatifs : on échoue avant d'ouvrir la transaction.
        requested = merge_requested_lines(
            (line.product_id, Quantity(line.quantity)) for line in command.lines
        )
        with self._uow_factory() as uow:
            products = uow.products.get_many_for_update(sorted(requested))
            order = place_order(requested, products, self._clock())
            for product in products.values():
                uow.products.save(product)
            uow.orders.add(order)
            uow.commit()
        return order
