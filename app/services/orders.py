"""Logique métier des commandes.

Principes :
1. Tout se passe dans UNE transaction : soit la commande est créée ET les stocks
   décrémentés, soit rien n'est modifié (rollback).
2. Toutes les vérifications ont lieu AVANT la première modification.
3. Les lignes produits sont verrouillées (SELECT ... FOR UPDATE) pour éviter que
   deux commandes simultanées ne vendent le même dernier article. Elles sont
   toujours verrouillées dans l'ordre croissant des id, pour éviter les deadlocks.
"""
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import (
    InsufficientStock,
    InvalidStatusTransition,
    OrderAlreadyCancelled,
    OrderNotFound,
    ProductNotFound,
)
from app.models import Order, OrderItem, OrderStatus, Product
from app.schemas import OrderItemIn


def list_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).order_by(Product.id)))


def _lock_products(db: Session, product_ids: list[int]) -> dict[int, Product]:
    rows = db.scalars(
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id)
        .with_for_update()
    ).all()
    return {p.id: p for p in rows}


def create_order(db: Session, items: list[OrderItemIn]) -> Order:
    try:
        # Si le même produit apparaît sur plusieurs lignes, on additionne : sinon
        # 2 lignes de 3 unités passeraient chacune un stock de 5.
        requested: dict[int, int] = defaultdict(int)
        for item in items:
            requested[item.product_id] += item.quantity
        product_ids = sorted(requested)

        products = _lock_products(db, product_ids)

        missing = [pid for pid in product_ids if pid not in products]
        if missing:
            raise ProductNotFound(
                f"Produit(s) inexistant(s) : {', '.join(map(str, missing))}",
                details={"product_ids": missing},
            )

        shortages = [
            {
                "product_id": pid,
                "product_name": products[pid].name,
                "requested": qty,
                "available": products[pid].stock,
            }
            for pid, qty in requested.items()
            if qty > products[pid].stock
        ]
        if shortages:
            raise InsufficientStock("Stock insuffisant.", details=shortages)

        # --- Toutes les vérifications sont passées : on modifie ---
        order = Order(status=OrderStatus.PENDING, total_amount=Decimal("0.00"))
        total = Decimal("0.00")
        for pid in product_ids:
            product, qty = products[pid], requested[pid]
            order.items.append(
                OrderItem(
                    product_id=pid,
                    product_name=product.name,
                    quantity=qty,
                    unit_price=product.unit_price,
                )
            )
            total += product.unit_price * qty
            product.stock -= qty
        order.total_amount = total

        db.add(order)
        db.commit()
        return order
    except Exception:
        db.rollback()
        raise


def list_orders(db: Session, status: OrderStatus | None = None) -> list[Order]:
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    if status:
        stmt = stmt.where(Order.status == status)
    return list(db.scalars(stmt))


def _get_order_locked(db: Session, order_id: int) -> Order:
    """Charge une commande en la verrouillant (évite deux annulations simultanées)."""
    order = db.scalars(
        select(Order).where(Order.id == order_id).with_for_update()
    ).one_or_none()
    if order is None:
        raise OrderNotFound(f"Commande {order_id} introuvable.")
    return order


def get_order(db: Session, order_id: int) -> Order:
    order = db.scalars(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    ).one_or_none()
    if order is None:
        raise OrderNotFound(f"Commande {order_id} introuvable.")
    return order


def cancel_order(db: Session, order_id: int) -> Order:
    """Annule une commande (en attente ou validée) et restitue le stock."""
    try:
        order = _get_order_locked(db, order_id)
        if order.status == OrderStatus.CANCELLED:
            raise OrderAlreadyCancelled(f"La commande {order_id} est déjà annulée.")

        product_ids = sorted(item.product_id for item in order.items)
        products = _lock_products(db, product_ids)
        for item in order.items:
            products[item.product_id].stock += item.quantity

        order.status = OrderStatus.CANCELLED
        db.commit()
        return order
    except Exception:
        db.rollback()
        raise


def validate_order(db: Session, order_id: int) -> Order:
    """Passe une commande de « En attente » à « Validée » (le stock est déjà réservé)."""
    try:
        order = _get_order_locked(db, order_id)
        if order.status != OrderStatus.PENDING:
            raise InvalidStatusTransition(
                f"Seule une commande en attente peut être validée "
                f"(statut actuel : {order.status.value}).",
                details={"current_status": order.status.value},
            )
        order.status = OrderStatus.VALIDATED
        db.commit()
        return order
    except Exception:
        db.rollback()
        raise
