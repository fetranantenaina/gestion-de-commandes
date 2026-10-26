"""Concurrence : plusieurs transactions réelles en parallèle sur PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor

from app.application.use_cases.create_order import CreateOrderCommand, OrderLineCommand
from app.domain.errors import DomainError
from tests.integration.conftest import CLE_USB


def test_concurrent_orders_never_oversell(use_cases, sql):
    """Stock = 3. 6 clients commandent 2 unités en même temps : un seul doit passer."""

    def place(_):
        try:
            use_cases.create_order.execute(CreateOrderCommand([OrderLineCommand(CLE_USB, 2)]))
            return True
        except DomainError:
            return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(place, range(6)))

    assert results.count(True) == 1
    assert sql(f"SELECT stock FROM products WHERE id = {CLE_USB}").scalar_one() == 1
    assert sql("SELECT count(*) FROM orders").scalar_one() == 1


def test_concurrent_cancellations_restore_stock_once(use_cases, sql):
    order = use_cases.create_order.execute(CreateOrderCommand([OrderLineCommand(CLE_USB, 3)]))

    def cancel(_):
        try:
            use_cases.cancel_order.execute(order.id)
            return True
        except DomainError:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(cancel, range(4)))

    assert results.count(True) == 1
    assert sql(f"SELECT stock FROM products WHERE id = {CLE_USB}").scalar_one() == 3  # pas 6, pas 9
