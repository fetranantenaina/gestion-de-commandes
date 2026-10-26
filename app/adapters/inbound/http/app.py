"""Fabrique de l'application FastAPI. Reçoit les cas d'usage déjà assemblés (injection)."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.adapters.inbound.http.error_handlers import register_error_handlers
from app.adapters.inbound.http.routes import create_router
from app.application.use_cases import UseCases

STATIC_DIR = Path(__file__).parent / "static"


def create_app(use_cases: UseCases) -> FastAPI:
    app = FastAPI(title="Gestion de commandes")
    app.include_router(create_router(use_cases))
    register_error_handlers(app)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
