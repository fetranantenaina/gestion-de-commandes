"""Adaptateur sortant EN MÉMOIRE : prouve que l'application ne dépend pas de PostgreSQL.

Il imite la transaction : le Unit of Work travaille sur une COPIE et ne l'écrit dans
le « stockage » qu'au commit. Une erreur avant le commit ne laisse donc aucune trace.
"""
import copy
from decimal import Decimal

from app.domain.order import Order, OrderStatus
from app.domain.product import Product
from app.domain.value_objects import Money


class InMemoryStore:
    def __init__(self, products: list[Product] | None = None):
        self.products: dict[int, Product] = {p.id: p for p in products or []}
        self.orders: dict[int, Order] = {}
        self.next_order_id = 1


class _ProductRepo:
    def __init__(self, data):
        self._data = data

    def list_all(self):
        return sorted(self._data.values(), key=lambda p: p.id)

    def get_many_for_update(self, ids):
        return {i: self._data[i] for i in sorted(ids) if i in self._data}

    def save(self, product):
        self._data[product.id] = product


class _OrderRepo:
    def __init__(self, uow):
        self._uow = uow

    def add(self, order):
        order.id = self._uow.next_order_id
        self._uow.next_order_id += 1
        self._uow.order_data[order.id] = order

    def get(self, order_id):
        return self._uow.order_data.get(order_id)

    get_for_update = get

    def list(self, status: OrderStatus | None = None):
        orders = sorted(self._uow.order_data.values(), key=lambda o: o.id, reverse=True)
        return [o for o in orders if status is None or o.status == status]

    def save(self, order):
        self._uow.order_data[order.id] = order


class InMemoryUnitOfWork:
    def __init__(self, store: InMemoryStore):
        self._store = store

    def __enter__(self):
        self.product_data = copy.deepcopy(self._store.products)
        self.order_data = copy.deepcopy(self._store.orders)
        self.next_order_id = self._store.next_order_id
        self.products = _ProductRepo(self.product_data)
        self.orders = _OrderRepo(self)
        return self

    def __exit__(self, exc_type, exc, tb):
        pass  # rien n'est écrit sans commit

    def commit(self):
        self._store.products = self.product_data
        self._store.orders = self.order_data
        self._store.next_order_id = self.next_order_id

    def rollback(self):
        pass


def default_store() -> InMemoryStore:
    return InMemoryStore(
        [
            Product(1, "Stylo", Money(Decimal("2.50")), stock=100),
            Product(2, "Cahier", Money(Decimal("4.00")), stock=50),
            Product(3, "Clé USB", Money(Decimal("12.90")), stock=3),
        ]
    )
