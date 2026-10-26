from app.application.ports import UnitOfWorkFactory
from app.domain.errors import OrderNotFound
from app.domain.order import Order, OrderStatus
from app.domain.product import Product


class ListProducts:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self._uow_factory = uow_factory

    def execute(self) -> list[Product]:
        with self._uow_factory() as uow:
            return uow.products.list_all()


class ListOrders:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self._uow_factory = uow_factory

    def execute(self, status: OrderStatus | None = None) -> list[Order]:
        with self._uow_factory() as uow:
            return uow.orders.list(status)


class GetOrder:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self._uow_factory = uow_factory

    def execute(self, order_id: int) -> Order:
        with self._uow_factory() as uow:
            order = uow.orders.get(order_id)
        if order is None:
            raise OrderNotFound(f"Commande {order_id} introuvable.")
        return order
