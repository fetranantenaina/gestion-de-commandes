from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.exceptions import DomainError
from app.routers import orders, products

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Gestion de commandes")
app.include_router(products.router)
app.include_router(orders.router)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    """Format d'erreur uniforme : {"error": {"code", "message", "details"}}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
