"""Fixtures d'intégration : un VRAI PostgreSQL, initialisé avec db/script.sql.

La connexion vient du fichier .env (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST,
POSTGRES_PORT) ; la base utilisée est POSTGRES_TEST_DB (défaut : orders_test), créée
automatiquement si elle n'existe pas.

ATTENTION : les tables de cette base sont supprimées et recréées avant CHAQUE test.
Ne jamais mettre le nom de la base de développement dans POSTGRES_TEST_DB.
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
from app.config import database_url

SCRIPT_SQL = Path(__file__).parents[2] / "db" / "script.sql"

# Identifiants des produits insérés par script.sql (base neuve => ids 1..8)
CLAVIER, SOURIS, ECRAN, HDMI, CLE_USB, WEBCAM, CASQUE, TAPIS = range(1, 9)


def _test_db_name() -> str:
    return os.getenv("POSTGRES_TEST_DB", "orders_test")


@pytest.fixture(scope="session")
def engine():
    """Moteur vers la base de test (créée si besoin). Saute les tests si PostgreSQL est injoignable."""
    name = _test_db_name()
    if name == os.getenv("POSTGRES_DB"):
        pytest.exit("POSTGRES_TEST_DB doit être différente de POSTGRES_DB (les tables sont supprimées).")
    try:
        admin = create_engine(database_url("postgres"), isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
        admin.dispose()
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL injoignable : {exc.orig}")
    test_engine = create_engine(database_url(name))
    yield test_engine
    test_engine.dispose()


@pytest.fixture(autouse=True)
def database(engine):
    """Repart d'une base neuve construite par script.sql : le script EST testé."""
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS order_items, orders, products CASCADE")
        conn.exec_driver_sql(SCRIPT_SQL.read_text(encoding="utf-8"))


@pytest.fixture
def uow_factory(engine):
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
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
def sql(engine):
    def _sql(statement: str):
        with engine.begin() as conn:
            return conn.execute(text(statement))

    return _sql
