# Gestion de commandes

Petite application web pour consulter des produits, créer des commandes et suivre leur statut.

**Stack** : Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL 16 · HTML/JS natif (sans build) · pytest

## Lancer l'application

### Option 1 — Docker (le plus simple)

```bash
docker compose up --build
```

Puis ouvrir <http://localhost:8000>. La base est créée et le jeu de données initial chargé automatiquement.
Documentation interactive de l'API : <http://localhost:8000/docs>.

### Option 2 — En local

Prérequis : Python 3.11+ et un PostgreSQL accessible.

```bash
# 1. Base de données (ou : docker compose up -d db)
createdb orders        # utilisateur orders / mot de passe orders par défaut

# 2. Dépendances
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuration (optionnelle, la valeur ci-dessous est celle par défaut)
export DATABASE_URL=postgresql+psycopg://orders:orders@localhost:5432/orders

# 4. Tables + jeu de données initial (idempotent)
python -m app.seed

# 5. Démarrage
uvicorn app.main:app --reload
```

## Jeu de données initial

`app/seed.py` insère 8 produits. Deux servent aux cas limites :
- **Clé USB 64 Go** : stock de 3 (tester « stock insuffisant »)
- **Tapis de souris** : stock de 0 (rupture)

## Tests

```bash
pytest                      # SQLite, aucune installation requise (17 tests)
```

Sur PostgreSQL (recommandé : active en plus les 2 tests de concurrence) :

```bash
createdb orders_test
TEST_DATABASE_URL=postgresql+psycopg://orders:orders@localhost:5432/orders_test pytest
```

> ⚠️ Les tables de `TEST_DATABASE_URL` sont supprimées à chaque test : utiliser une base dédiée, jamais `orders`.

Les 6 cas demandés par l'énoncé sont couverts dans `tests/test_orders.py` (commande valide multi-produits,
stock insuffisant, quantité ≤ 0, produit inexistant, annulation + restitution, double annulation), plus :
atomicité, lignes en double, changement de prix après commande, transitions de statut.

## API

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/products` | Liste des produits |
| POST | `/api/orders` | Crée une commande `{"items":[{"product_id":1,"quantity":2}]}` → 201 |
| GET | `/api/orders` | Liste des commandes (`?status=PENDING\|VALIDATED\|CANCELLED`) |
| GET | `/api/orders/{id}` | Détail d'une commande |
| POST | `/api/orders/{id}/validate` | En attente → Validée |
| POST | `/api/orders/{id}/cancel` | Annule et restitue le stock |

| Situation | Code HTTP | `error.code` |
|---|---|---|
| Quantité ≤ 0, liste vide, JSON invalide | 422 | (validation Pydantic) |
| Produit inexistant / commande inexistante | 404 | `product_not_found` / `order_not_found` |
| Stock insuffisant | 409 | `insufficient_stock` (détail : demandé vs disponible par produit) |
| Commande déjà annulée | 409 | `order_already_cancelled` |
| Validation d'une commande non « en attente » | 409 | `invalid_status_transition` |

## Organisation du code

```
app/
  models.py          Tables SQLAlchemy + contraintes CHECK
  schemas.py         Validation des entrées / forme des sorties (Pydantic)
  exceptions.py      Erreurs métier -> codes HTTP
  services/orders.py LOGIQUE MÉTIER (aucune dépendance à HTTP)
  routers/           Routes fines : parsent la requête, appellent le service
  main.py            Assemblage + gestionnaire d'erreurs
  seed.py            Jeu de données
  static/index.html  Interface
tests/               Tests d'API (pytest + TestClient) et de concurrence
```

La logique métier est isolée dans `services/` : les routes ne contiennent aucune règle, ce qui garde le code
lisible et testable.

## Choix techniques et hypothèses

**Cycle de vie des statuts.** L'énoncé demande de mettre à jour le stock « après validation de la commande »
et de restituer le stock à l'annulation. J'ai interprété ainsi :
- à la création, toutes les vérifications sont faites, puis la commande est enregistrée au statut **En attente**
  et le **stock est immédiatement réservé** (sinon deux clients pourraient commander le dernier article) ;
- `validate` fait passer **En attente → Validée** (le stock est déjà réservé, il ne bouge pas) ;
- `cancel` est possible depuis **En attente** ou **Validée** et restitue le stock ; depuis **Annulée**, c'est refusé.

Si la règle voulue était « le stock ne baisse qu'à la validation », il suffirait de déplacer la décrémentation
de `create_order` vers `validate_order` ; en revanche il faudrait alors revérifier le stock à ce moment-là.

**Atomicité.** Création et annulation s'exécutent dans une seule transaction. Toutes les vérifications précèdent
la première écriture, et un `rollback` explicite couvre les erreurs inattendues : une commande refusée ne laisse
aucune trace, et les stocks ne sont jamais modifiés.

**Concurrence.** Les produits concernés sont verrouillés avec `SELECT ... FOR UPDATE`, toujours dans l'ordre
croissant des identifiants (évite les deadlocks). Deux commandes simultanées sur le dernier article : l'une
passe, l'autre reçoit un 409 (testé avec 6 threads). L'annulation verrouille aussi la commande, donc deux
annulations simultanées ne restituent le stock qu'une fois.

**Lignes en double.** Si un produit apparaît plusieurs fois dans une commande, les quantités sont additionnées
avant la vérification du stock (sinon 2 lignes de 3 passeraient chacune un stock de 5) puis fusionnées en une ligne.

**Intégrité en profondeur.** Contraintes `CHECK` en base (`stock >= 0`, `quantity > 0`, `unit_price >= 0`) :
même un bug applicatif ne pourrait pas créer un stock négatif.

**Argent.** `NUMERIC(10,2)` en base et `Decimal` en Python, jamais de `float`. L'API renvoie les montants
sous forme de chaînes (`"204.30"`) pour éviter toute perte de précision côté client.

**Historique figé.** Le nom et le prix unitaire sont copiés dans chaque ligne de commande : modifier un produit
plus tard ne change ni le total ni le contenu des commandes passées.

**Validation à deux niveaux.** Pydantic rejette les entrées mal formées (422) ; le service vérifie ce qui dépend
des données (existence, stock).

**Pas de migrations.** `create_all` suffit pour une v1. Pour la production, j'ajouterais Alembic.

## Pistes d'amélioration

- Migrations Alembic, authentification, pagination de `/api/orders`
- CRUD produits (hors périmètre de l'énoncé)
- Clé d'idempotence sur `POST /api/orders` pour éviter les doublons en cas de double clic / retry réseau
- CI (GitHub Actions) avec service PostgreSQL
