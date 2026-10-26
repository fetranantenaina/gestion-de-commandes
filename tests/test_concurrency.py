"""Test de concurrence : nécessite PostgreSQL (SELECT ... FOR UPDATE réel)."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app.exceptions import InsufficientStock
from app.models import Order, Product
from app.schemas import OrderItemIn
from app.services import orders as service
from tests.conftest import CLE_USB, IS_POSTGRES, TestingSession

pytestmark = pytest.mark.skipif(not IS_POSTGRES, reason="nécessite PostgreSQL")


def test_concurrent_orders_never_oversell():
    """Stock = 3. 6 clients commandent 2 unités en même temps : un seul doit passer."""

    def place_order(_):
        with TestingSession() as db:
            try:
                service.create_order(db, [OrderItemIn(product_id=CLE_USB, quantity=2)])
                return True
            except InsufficientStock:
                return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(place_order, range(6)))

    assert results.count(True) == 1
    with TestingSession() as db:
        assert db.get(Product, CLE_USB).stock == 1
        assert len(db.scalars(select(Order)).all()) == 1


def test_concurrent_cancellations_restore_stock_once():
    with TestingSession() as db:
        order = service.create_order(db, [OrderItemIn(product_id=CLE_USB, quantity=3)])
        order_id = order.id

    def cancel(_):
        with TestingSession() as db:
            try:
                service.cancel_order(db, order_id)
                return True
            except Exception:
                return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(cancel, range(4)))

    assert results.count(True) == 1
    with TestingSession() as db:
        assert db.get(Product, CLE_USB).stock == 3  # pas 6, pas 9
