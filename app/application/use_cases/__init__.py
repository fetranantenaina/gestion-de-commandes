"""Cas d'usage de l'application + petit conteneur pour les assembler."""
from dataclasses import dataclass

from app.application.ports import UnitOfWorkFactory
from app.application.use_cases.cancel_order import CancelOrder
from app.application.use_cases.create_order import CreateOrder
from app.application.use_cases.queries import GetOrder, ListOrders, ListProducts
from app.application.use_cases.validate_order import ValidateOrder


@dataclass(frozen=True)
class UseCases:
    create_order: CreateOrder
    cancel_order: CancelOrder
    validate_order: ValidateOrder
    list_orders: ListOrders
    get_order: GetOrder
    list_products: ListProducts


def build_use_cases(uow_factory: UnitOfWorkFactory) -> UseCases:
    return UseCases(
        create_order=CreateOrder(uow_factory),
        cancel_order=CancelOrder(uow_factory),
        validate_order=ValidateOrder(uow_factory),
        list_orders=ListOrders(uow_factory),
        get_order=GetOrder(uow_factory),
        list_products=ListProducts(uow_factory),
    )
