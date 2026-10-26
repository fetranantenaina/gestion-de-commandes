from app.application.ports import UnitOfWorkFactory
from app.domain.errors import OrderNotFound
from app.domain.order import Order
from app.domain.services import cancel_order


class CancelOrder:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self._uow_factory = uow_factory

    def execute(self, order_id: int) -> Order:
        with self._uow_factory() as uow:
            order = uow.orders.get_for_update(order_id)
            if order is None:
                raise OrderNotFound(f"Commande {order_id} introuvable.")
            products = uow.products.get_many_for_update(order.product_ids)
            cancel_order(order, products)
            for product in products.values():
                uow.products.save(product)
            uow.orders.save(order)
            uow.commit()
        return order
