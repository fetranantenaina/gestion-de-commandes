"""Erreurs métier. Chacune est traduite en réponse HTTP JSON par main.py."""


class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str, details: list | dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class ProductNotFound(DomainError):
    status_code = 404
    code = "product_not_found"


class OrderNotFound(DomainError):
    status_code = 404
    code = "order_not_found"


class InsufficientStock(DomainError):
    status_code = 409
    code = "insufficient_stock"


class OrderAlreadyCancelled(DomainError):
    status_code = 409
    code = "order_already_cancelled"


class InvalidStatusTransition(DomainError):
    status_code = 409
    code = "invalid_status_transition"
