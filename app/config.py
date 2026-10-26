import os

# PostgreSQL sur le port 5432 (voir docker-compose.yml)
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://orders:orders@localhost:5432/orders"
)
