"""Schémas Pydantic (validation des entrées, forme des sorties)."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    unit_price: Decimal
    stock: int


class OrderItemIn(BaseModel):
    product_id: int
    # gt=0 : une quantité nulle ou négative est rejetée (422) avant toute logique métier.
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    total_amount: Decimal
    status: OrderStatus
    items: list[OrderItemOut]
