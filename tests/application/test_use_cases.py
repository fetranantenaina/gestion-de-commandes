"""Tests des CAS D'USAGE avec un adaptateur en mémoire (pas de base de données)."""
from decimal import Decimal

import pytest

from app.application.use_cases import build_use_cases
from app.application.use_cases.create_order import CreateOrderCommand, OrderLineCommand
from app.domain import errors
from app.domain.order import OrderStatus
from tests.fakes import InMemoryUnitOfWork, default_store


@pytest.fixture
def store():
    return default_store()


@pytest.fixture
def uc(store):
    return build_use_cases(lambda: InMemoryUnitOfWork(store))


def command(*lines):
    return CreateOrderCommand([OrderLineCommand(pid, qty) for pid, qty in lines])


def test_create_order_persists_order_and_updates_stock(uc, store):
    order = uc.create_order.execute(command((1, 2), (2, 1)))

    assert order.id == 1 and order.total.amount == Decimal("9.00")
    assert store.products[1].stock == 98 and store.products[2].stock == 49
    assert uc.list_orders.execute() == [order]


@pytest.mark.parametrize("qty", [0, -3])
def test_invalid_quantity_touches_nothing(uc, store, qty):
    with pytest.raises(errors.InvalidQuantity):
        uc.create_order.execute(command((1, qty)))
    assert store.products[1].stock == 100 and not store.orders


def test_failed_order_is_atomic(uc, store):
    with pytest.raises(errors.InsufficientStock):
        uc.create_order.execute(command((1, 5), (3, 10)))
    assert store.products[1].stock == 100 and store.products[3].stock == 3
    assert not store.orders


def test_unknown_product(uc, store):
    with pytest.raises(errors.ProductNotFound):
        uc.create_order.execute(command((1, 1), (999, 1)))
    assert store.products[1].stock == 100


def test_cancel_restores_stock_and_cannot_be_repeated(uc, store):
    order = uc.create_order.execute(command((1, 2), (2, 5)))

    cancelled = uc.cancel_order.execute(order.id)
    assert cancelled.status == OrderStatus.CANCELLED
    assert store.products[1].stock == 100 and store.products[2].stock == 50

    with pytest.raises(errors.OrderAlreadyCancelled):
        uc.cancel_order.execute(order.id)
    assert store.products[1].stock == 100


def test_unknown_order(uc):
    for action in (uc.cancel_order, uc.validate_order, uc.get_order):
        with pytest.raises(errors.OrderNotFound):
            action.execute(42)


def test_validate_then_cancel(uc, store):
    order = uc.create_order.execute(command((1, 2)))
    assert uc.validate_order.execute(order.id).status == OrderStatus.VALIDATED
    uc.cancel_order.execute(order.id)
    assert store.products[1].stock == 100
