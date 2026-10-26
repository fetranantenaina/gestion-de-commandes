"""Routes : parsent la requête, appellent UN cas d'usage, formatent la réponse. Aucune règle métier."""
from fastapi import APIRouter

from app.adapters.inbound.http.schemas import (
    CreateOrderRequest,
    OrderResponse,
    ProductResponse,
)
from app.application.use_cases import UseCases
from app.application.use_cases.create_order import CreateOrderCommand, OrderLineCommand
from app.domain.order import OrderStatus


def create_router(use_cases: UseCases) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/products", response_model=list[ProductResponse], tags=["products"])
    def list_products():
        return [ProductResponse.from_domain(p) for p in use_cases.list_products.execute()]

    @router.post("/orders", response_model=OrderResponse, status_code=201, tags=["orders"])
    def create_order(payload: CreateOrderRequest):
        command = CreateOrderCommand(
            lines=[OrderLineCommand(i.product_id, i.quantity) for i in payload.items]
        )
        return OrderResponse.from_domain(use_cases.create_order.execute(command))

    @router.get("/orders", response_model=list[OrderResponse], tags=["orders"])
    def list_orders(status: OrderStatus | None = None):
        return [OrderResponse.from_domain(o) for o in use_cases.list_orders.execute(status)]

    @router.get("/orders/{order_id}", response_model=OrderResponse, tags=["orders"])
    def get_order(order_id: int):
        return OrderResponse.from_domain(use_cases.get_order.execute(order_id))

    @router.post("/orders/{order_id}/validate", response_model=OrderResponse, tags=["orders"])
    def validate_order(order_id: int):
        return OrderResponse.from_domain(use_cases.validate_order.execute(order_id))

    @router.post("/orders/{order_id}/cancel", response_model=OrderResponse, tags=["orders"])
    def cancel_order(order_id: int):
        return OrderResponse.from_domain(use_cases.cancel_order.execute(order_id))

    return router
