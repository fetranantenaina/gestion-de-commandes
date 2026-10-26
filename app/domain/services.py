"""Services du domaine : règles qui impliquent PLUSIEURS agrégats (commande + produits).

Fonctions pures : elles ne lisent ni n'écrivent nulle part, elles manipulent des objets
déjà chargés. Toutes les vérifications ont lieu AVANT la première modification, donc un
échec ne laisse aucun produit à moitié modifié.
"""
from collections.abc import Iterable, Mapping
from datetime import datetime

from app.domain.errors import EmptyOrder, InsufficientStock, ProductNotFound
from app.domain.order import Order, OrderLine
from app.domain.product import Product
from app.domain.value_objects import Quantity


def merge_requested_lines(lines: Iterable[tuple[int, Quantity]]) -> dict[int, Quantity]:
    """Additionne les quantités d'un même produit présent sur plusieurs lignes.

    Sans cela, 2 lignes de 3 unités passeraient chacune un stock de 5.
    """
    merged: dict[int, Quantity] = {}
    for product_id, quantity in lines:
        merged[product_id] = merged[product_id] + quantity if product_id in merged else quantity
    if not merged:
        raise EmptyOrder("Une commande doit contenir au moins un produit.")
    return merged


def place_order(
    requested: Mapping[int, Quantity],
    products: Mapping[int, Product],
    created_at: datetime,
) -> Order:
    """Vérifie tout, réserve le stock, construit la commande (statut : en attente)."""
    missing = sorted(pid for pid in requested if pid not in products)
    if missing:
        raise ProductNotFound(
            f"Produit(s) inexistant(s) : {', '.join(map(str, missing))}",
            {"product_ids": missing},
        )

    shortages = [
        shortage
        for pid, quantity in requested.items()
        if (shortage := products[pid].stock_shortage(quantity))
    ]
    if shortages:
        raise InsufficientStock(shortages)

    lines = []
    for pid in sorted(requested):
        product, quantity = products[pid], requested[pid]
        product.reserve(quantity)
        lines.append(OrderLine(pid, product.name, quantity, product.unit_price))
    return Order(lines=lines, created_at=created_at)


def cancel_order(order: Order, products: Mapping[int, Product]) -> None:
    """Annule la commande puis restitue le stock. Refuse une seconde annulation."""
    order.cancel()  # lève OrderAlreadyCancelled AVANT toute restitution
    for line in order.lines:
        products[line.product_id].restock(line.quantity)
