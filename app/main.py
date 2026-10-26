"""Racine de composition : le SEUL endroit qui connaît toutes les couches et les assemble.

    PostgreSQL ──▶ SqlAlchemyUnitOfWork ──▶ cas d'usage ──▶ API HTTP

Lancement : uvicorn app.main:app
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.inbound.http.app import create_app
from app.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.application.use_cases import build_use_cases
from app.config import database_url

engine = create_engine(database_url(), pool_pre_ping=True)
# expire_on_commit=False : les objets restent lisibles après le commit
session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

use_cases = build_use_cases(lambda: SqlAlchemyUnitOfWork(session_factory))
app = create_app(use_cases)
