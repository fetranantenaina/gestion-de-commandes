"""Unit of Work PostgreSQL : une session SQLAlchemy = une transaction."""
from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from app.adapters.outbound.persistence.repositories import (
    SqlAlchemyOrderRepository,
    SqlAlchemyProductRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.products = SqlAlchemyProductRepository(self._session)
        self.orders = SqlAlchemyOrderRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                self._session.rollback()  # toute erreur annule la transaction entière
        finally:
            self._session.close()  # libère aussi les verrous si on n'a pas commité

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
