"""Fixtures de test.

Par défaut les tests tournent sur SQLite (aucune installation requise).
Pour les lancer sur PostgreSQL (recommandé, et nécessaire pour le test de
concurrence) :

    TEST_DATABASE_URL=postgresql+psycopg://orders:orders@localhost:5432/orders_test pytest

ATTENTION : les tables de cette base sont supprimées puis recréées à chaque test.
Ne jamais pointer TEST_DATABASE_URL vers la base de développement.
"""
import os
from decimal import Decimal

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL  # avant l'import de app.database

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base, Product

_connect_args = {"check_same_thread": False} if TEST_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(TEST_DATABASE_URL, connect_args=_connect_args)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

IS_POSTGRES = engine.dialect.name == "postgresql"

# Ids fixes (tables recréées à chaque test => séquences repartent de 1)
STYLO, CAHIER, CLE_USB = 1, 2, 3


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add_all(
            [
                Product(name="Stylo", unit_price=Decimal("2.50"), stock=100),
                Product(name="Cahier", unit_price=Decimal("4.00"), stock=50),
                Product(name="Clé USB", unit_price=Decimal("12.90"), stock=3),
            ]
        )
        db.commit()
    yield


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def stock_of(client):
    def _stock_of(product_id: int) -> int:
        products = client.get("/api/products").json()
        return next(p["stock"] for p in products if p["id"] == product_id)

    return _stock_of
