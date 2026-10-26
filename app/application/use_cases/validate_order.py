from app.application.ports import UnitOfWorkFactory
from app.domain.errors import OrderNotFound
from app.domain.order import Order


class ValidateOrder:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self._uow_factory = uow_factory

    def execute(self, order_id: int) -> Order:
        with self._uow_factory() as uow:
            order = uow.orders.get_for_update(order_id)
            if order is None:
                raise OrderNotFound(f"Commande {order_id} introuvable.")
            order.validate()
            uow.orders.save(order)
            uow.commit()
        return order
