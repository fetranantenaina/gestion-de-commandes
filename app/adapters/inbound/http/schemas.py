"""Contrat JSON de l'API (DTO Pydantic) et traduction domaine -> réponse.

Pydantic ne valide ici que la FORME (types, champs présents). Les règles métier
(quantité > 0, stock suffisant…) restent dans le domaine.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.domain.order import Order, OrderStatus
from app.domain.product import Product


class OrderLineRequest(BaseModel):
    product_id: int
    quantity: int


class CreateOrderRequest(BaseModel):
    items: list[OrderLineRequest]


class ProductResponse(BaseModel):
    id: int
    name: str
    unit_price: Decimal
    stock: int

    @classmethod
    def from_domain(cls, product: Product) -> "ProductResponse":
        return cls(
            id=product.id,
            name=product.name,
            unit_price=product.unit_price.amount,
            stock=product.stock,
        )


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderResponse(BaseModel):
    id: int
    created_at: datetime
    total_amount: Decimal
    status: OrderStatus
    items: list[OrderItemResponse]

    @classmethod
    def from_domain(cls, order: Order) -> "OrderResponse":
        return cls(
            id=order.id,
            created_at=order.created_at,
            total_amount=order.total.amount,
            status=order.status,
            items=[
                OrderItemResponse(
                    product_id=line.product_id,
                    product_name=line.product_name,
                    quantity=line.quantity.value,
                    unit_price=line.unit_price.amount,
                    line_total=line.total.amount,
                )
                for line in order.lines
            ],
        )
