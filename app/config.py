"""Configuration : lue dans les variables d'environnement, chargées depuis le fichier .env.

Les variables déjà définies (ex. par Docker Compose) ont priorité sur le fichier .env.
Aucun identifiant n'est écrit en dur dans le code.
"""
import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()  # cherche .env depuis ce fichier en remontant vers la racine du projet


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Variable d'environnement manquante : {name}. "
            "Copiez .env.example vers .env et renseignez les valeurs."
        )
    return value


def database_url(database: str | None = None) -> URL:
    """URL de connexion PostgreSQL construite à partir des variables POSTGRES_*.

    URL.create échappe correctement les caractères spéciaux du mot de passe (@, :, / ...).
    """
    return URL.create(
        "postgresql+psycopg",
        username=_required("POSTGRES_USER"),
        password=_required("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=database or _required("POSTGRES_DB"),
    )
