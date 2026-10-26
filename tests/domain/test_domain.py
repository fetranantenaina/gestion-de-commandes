"""Tests du DOMAINE : Python pur, aucune base, aucun framework, exécution instantanée."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain import errors
from app.domain.order import Order, OrderLine, OrderStatus
from app.domain.product import Product
from app.domain.services import cancel_order, merge_requested_lines, place_order
from app.domain.value_objects import Money, Quantity

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_products() -> dict[int, Product]:
    return {
        1: Product(1, "Stylo", Money(Decimal("2.50")), stock=100),
        2: Product(2, "Cahier", Money(Decimal("4.00")), stock=50),
        3: Product(3, "Clé USB", Money(Decimal("12.90")), stock=3),
    }


# ----- Objets-valeurs -----
@pytest.mark.parametrize("bad", [0, -1, -50, True, 1.5, "2"])
def test_quantity_must_be_strictly_positive_integer(bad):
    with pytest.raises(errors.InvalidQuantity):
        Quantity(bad)


def test_money_is_rounded_to_cents_and_never_negative():
    assert Money(Decimal("2.505")).amount == Decimal("2.51")
    assert (Money(Decimal("0.10")) * 3).amount == Decimal("0.30")  # pas de 0.30000000000000004
    with pytest.raises(ValueError):
        Money(Decimal("-1"))


# ----- Product -----
def test_product_reserve_and_restock():
    p = make_products()[3]
    p.reserve(Quantity(3))
    assert p.stock == 0
    p.restock(Quantity(2))
    assert p.stock == 2


def test_product_cannot_reserve_more_than_stock():
    p = make_products()[3]
    with pytest.raises(errors.InsufficientStock):
        p.reserve(Quantity(4))
    assert p.stock == 3


# ----- Service place_order -----
def test_place_order_computes_total_and_reserves_stock():
    products = make_products()
    order = place_order({1: Quantity(2), 2: Quantity(1)}, products, NOW)

    assert order.status == OrderStatus.PENDING
    assert order.total == Money(Decimal("9.00"))
    assert products[1].stock == 98 and products[2].stock == 49


def test_place_order_unknown_product():
    products = make_products()
    with pytest.raises(errors.ProductNotFound) as exc:
        place_order({1: Quantity(1), 999: Quantity(1)}, products, NOW)
    assert exc.value.details == {"product_ids": [999]}
    assert products[1].stock == 100


def test_place_order_reports_all_shortages_and_changes_nothing():
    products = make_products()
    with pytest.raises(errors.InsufficientStock) as exc:
        place_order({1: Quantity(5), 3: Quantity(10)}, products, NOW)
    assert exc.value.details == [
        {"product_id": 3, "product_name": "Clé USB", "requested": 10, "available": 3}
    ]
    assert products[1].stock == 100  # le produit valide n'a pas été touché


def test_duplicate_lines_are_summed():
    merged = merge_requested_lines([(3, Quantity(2)), (3, Quantity(2))])
    assert merged == {3: Quantity(4)}
    with pytest.raises(errors.InsufficientStock):
        place_order(merged, make_products(), NOW)


def test_empty_order_is_rejected():
    with pytest.raises(errors.EmptyOrder):
        merge_requested_lines([])


# ----- Cycle de vie / annulation -----
def test_cancel_restores_stock_once():
    products = make_products()
    order = place_order({1: Quantity(2)}, products, NOW)
    order.id = 1

    cancel_order(order, products)
    assert order.status == OrderStatus.CANCELLED and products[1].stock == 100

    with pytest.raises(errors.OrderAlreadyCancelled):
        cancel_order(order, products)
    assert products[1].stock == 100  # pas de double restitution


def test_status_transitions():
    line = OrderLine(1, "Stylo", Quantity(1), Money(Decimal("2.50")))
    order = Order(lines=[line], created_at=NOW)

    order.validate()
    assert order.status == OrderStatus.VALIDATED
    with pytest.raises(errors.InvalidStatusTransition):
        order.validate()

    order.cancel()  # une commande validée peut être annulée
    with pytest.raises(errors.InvalidStatusTransition):
        order.validate()


def test_order_requires_at_least_one_line():
    with pytest.raises(errors.EmptyOrder):
        Order(lines=[], created_at=NOW)
