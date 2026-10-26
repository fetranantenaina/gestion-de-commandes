"""Traduction des erreurs du domaine en réponses HTTP.

C'est ici (et seulement ici) que l'on décide qu'un stock insuffisant vaut « 409 ».
Le domaine, lui, ne connaît pas HTTP.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain import errors

HTTP_STATUS: dict[type[errors.DomainError], int] = {
    errors.InvalidQuantity: 422,
    errors.EmptyOrder: 422,
    errors.ProductNotFound: 404,
    errors.OrderNotFound: 404,
    errors.InsufficientStock: 409,
    errors.OrderAlreadyCancelled: 409,
    errors.InvalidStatusTransition: 409,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(errors.DomainError)
    async def handle_domain_error(_: Request, exc: errors.DomainError):
        return JSONResponse(
            status_code=HTTP_STATUS.get(type(exc), 400),
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )
