"""Fixtures d'intégration : un VRAI PostgreSQL, initialisé avec db/script.sql.

Par défaut : postgresql://orders:orders@localhost:5432/orders_test
(base créée par docker-compose via db/create-test-db.sql).

ATTENTION : les tables de cette base sont supprimées et recréées avant CHAQUE test.
Ne jamais pointer TEST_DATABASE_URL vers la base de développement.
"""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.adapters.inbound.http.app import create_app
from app.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases import build_use_cases

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://orders:orders@localhost:5432/orders_test"
)
SCRIPT_SQL = Path(__file__).parents[2] / "db" / "script.sql"

engine = create_engine(TEST_DATABASE_URL)
session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Identifiants des produits insérés par script.sql (base neuve => ids 1..8)
CLAVIER, SOURIS, ECRAN, HDMI, CLE_USB, WEBCAM, CASQUE, TAPIS = range(1, 9)


@pytest.fixture(autouse=True)
def database():
    """Repart d'une base neuve construite par script.sql : le script EST testé."""
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("DROP TABLE IF EXISTS order_items, orders, products CASCADE")
            conn.exec_driver_sql(SCRIPT_SQL.read_text(encoding="utf-8"))
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL injoignable ({TEST_DATABASE_URL}) : {exc.orig}")


@pytest.fixture
def uow_factory():
    return lambda: SqlAlchemyUnitOfWork(session_factory)


@pytest.fixture
def use_cases(uow_factory):
    return build_use_cases(uow_factory)


@pytest.fixture
def client(use_cases):
    return TestClient(create_app(use_cases))


@pytest.fixture
def stock_of(client):
    def _stock_of(product_id: int) -> int:
        return next(p["stock"] for p in client.get("/api/products").json() if p["id"] == product_id)

    return _stock_of


@pytest.fixture
def sql():
    def _sql(statement: str):
        with engine.begin() as conn:
            return conn.execute(text(statement))

    return _sql
