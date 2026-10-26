"""Modèles SQLAlchemy : ils décrivent les TABLES, pas le domaine.

Le schéma est créé par db/script.sql ; ces classes ne servent qu'à lire/écrire.
Les objets du domaine (Product, Order…) n'en dépendent jamais : c'est le rôle des
repositories de traduire dans les deux sens.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProductRow(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(Integer)


class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20))

    items: Mapped[list["OrderItemRow"]] = relationship(
        cascade="all, delete-orphan", order_by="OrderItemRow.id"
    )


class OrderItemRow(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
