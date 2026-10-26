"""Ports SORTANTS : ce dont l'application a besoin, exprimé dans le langage du domaine.

L'application dépend de ces interfaces ; ce sont les adaptateurs (PostgreSQL, mémoire…)
qui les implémentent. Le sens de dépendance est donc : adaptateurs → application → domaine.
"""
from types import TracebackType
from typing import Callable, Mapping, Protocol, Sequence

from app.domain.order import Order, OrderStatus
from app.domain.product import Product


class ProductRepository(Protocol):
    def list_all(self) -> list[Product]: ...

    def get_many_for_update(self, product_ids: Sequence[int]) -> Mapping[int, Product]:
        """Charge ET verrouille les produits (ordre croissant des ids : pas de deadlock)."""

    def save(self, product: Product) -> None: ...


class OrderRepository(Protocol):
    def add(self, order: Order) -> None:
        """Persiste une nouvelle commande et renseigne `order.id`."""

    def get(self, order_id: int) -> Order | None: ...

    def get_for_update(self, order_id: int) -> Order | None:
        """Charge ET verrouille la commande (évite deux annulations simultanées)."""

    def list(self, status: OrderStatus | None = None) -> list[Order]: ...

    def save(self, order: Order) -> None: ...


class UnitOfWork(Protocol):
    """Une transaction : tout ce qui est fait dedans est validé ensemble, ou rien."""

    products: ProductRepository
    orders: OrderRepository

    def __enter__(self) -> "UnitOfWork": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
