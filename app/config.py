import os

# PostgreSQL sur le port 5433 (voir docker-compose.yml)
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://orders:orders@localhost:5433/orders"
)
