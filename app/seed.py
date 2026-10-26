"""Crée les tables et charge le jeu de données initial (idempotent).

Usage : python -m app.seed
"""
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal, engine
from app.models import Base, Product

SEED_PRODUCTS = [
    ("Clavier mécanique", "89.90", 25),
    ("Souris sans fil", "24.50", 40),
    ("Écran 24 pouces", "149.00", 10),
    ("Câble HDMI 2 m", "7.90", 100),
    ("Clé USB 64 Go", "12.90", 3),   # stock faible : pratique pour tester le stock insuffisant
    ("Webcam HD", "39.99", 15),
    ("Casque audio", "59.00", 8),
    ("Tapis de souris", "9.90", 0),  # rupture de stock
]


def seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalars(select(Product).limit(1)).first():
            print("Produits déjà présents : rien à faire.")
            return
        db.add_all(
            Product(name=n, unit_price=Decimal(p), stock=s) for n, p, s in SEED_PRODUCTS
        )
        db.commit()
        print(f"{len(SEED_PRODUCTS)} produits insérés.")


if __name__ == "__main__":
    seed()
