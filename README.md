# Gestion de commandes

Petite application web pour consulter des produits, créer des commandes et suivre leur statut.

**Stack** : Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL 16 · HTML/JS natif · pytest
**Architecture** : hexagonale (ports & adaptateurs) + Domain-Driven Design

## Configuration : fichier `.env`

Tous les identifiants et ports sont dans un fichier **`.env`** (jamais versionné). Au premier usage :

```powershell
Copy-Item .env.example .env      # Linux/macOS : cp .env.example .env
```

puis éditer `.env` (au minimum `POSTGRES_PASSWORD`).

| Variable | Rôle | Défaut |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Identifiants et base PostgreSQL | *(obligatoire)* |
| `POSTGRES_TEST_DB` | Base des tests d'intégration (créée automatiquement) | `orders_test` |
| `POSTGRES_HOST` | Hôte PostgreSQL vu depuis votre machine | `localhost` |
| `POSTGRES_PORT` | Port PostgreSQL exposé sur votre machine | `5432` |
| `APP_PORT` | Port de l'application exposé sur votre machine | `8000` |

Docker Compose lit ce même fichier : aucun mot de passe n'est écrit dans `docker-compose.yml` ni dans le code.
Dans Docker, l'application joint la base via `db:5432` (réglé automatiquement, indépendamment de `POSTGRES_PORT`).

> Le mot de passe n'est appliqué qu'à la **création** du volume de la base. Pour le changer après un premier lancement :
> `docker compose down -v` puis relancer.

## Lancer l'application

### Option 1 — Docker (le plus simple)

```bash
docker compose up --build
```

- Application : <http://localhost:8000> (API interactive : <http://localhost:8000/docs>)
- PostgreSQL : `localhost:5432` avec les identifiants du `.env`

Au premier démarrage, PostgreSQL exécute automatiquement `db/script.sql` (schéma + jeu de données).
Pour repartir de zéro : `docker compose down -v && docker compose up --build`.

**Erreur « port is not available » ?** Un autre programme utilise déjà ce port (souvent un PostgreSQL installé sur la
machine). Changer `POSTGRES_PORT` (ou `APP_PORT`) dans `.env`, par exemple `POSTGRES_PORT=5433`.
L'application dans Docker n'est pas affectée ; seuls `psql` et les tests lisent ce port.

### Option 2 — En local (Python + base dans Docker)

Prérequis : Python 3.11+ et Docker. Seule la base tourne dans Docker ; `db/script.sql` s'y exécute automatiquement.
Aucune base à créer à la main.

**Windows (PowerShell)**
```powershell
Copy-Item .env.example .env       # puis éditer .env
docker compose up -d db

python -m venv .venv
.venv\Scripts\Activate.ps1      # si refusé : Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt

uvicorn app.main:app --reload
```

**Linux / macOS**
```bash
cp .env.example .env              # puis éditer .env
docker compose up -d db

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Avec un PostgreSQL déjà installé (sans Docker) : créer l'utilisateur et la base correspondant au `.env`, renseigner
`POSTGRES_HOST` / `POSTGRES_PORT`, puis exécuter le script :
`psql -h localhost -p 5432 -U <user> -d <base> -f db/script.sql`
(PowerShell : définir d'abord `$env:PGPASSWORD="<mot de passe>"`).

## Base de données : `db/script.sql`

Le script contient **le schéma** (tables, clés, contraintes `CHECK`, index) **et le jeu de données initial**.
Il est idempotent : `CREATE ... IF NOT EXISTS`, et les produits ne sont insérés que si la table est vide.

Produits de test : 8 produits dont **Clé USB 64 Go** (stock 3 → tester le stock insuffisant) et
**Tapis de souris** (stock 0 → rupture).

## Tests

```bash
pytest
```

| Niveau | Dossier | Dépendances | Ce qui est vérifié |
|---|---|---|---|
| Domaine | `tests/domain` | aucune | règles métier pures (objets-valeurs, agrégats, services) |
| Cas d'usage | `tests/application` | aucune (faux en mémoire) | orchestration, atomicité, erreurs |
| Intégration | `tests/integration` | PostgreSQL + `.env` | API HTTP complète, `script.sql`, contraintes SQL, **concurrence** |

Les tests unitaires s'exécutent en quelques millisecondes sans base ni `.env`. Les tests d'intégration lisent le
`.env`, utilisent la base `POSTGRES_TEST_DB` (créée automatiquement si elle n'existe pas) et se **sautent
proprement** si PostgreSQL est injoignable.

> ⚠️ Les tables de la base de test sont supprimées puis recréées depuis `script.sql` avant chaque test.
> `POSTGRES_TEST_DB` doit être différente de `POSTGRES_DB` (les tests refusent de démarrer sinon).

Les 6 cas de l'énoncé sont dans `tests/integration/test_api.py` (et leur équivalent métier dans `tests/domain`).

## Architecture

```
          ┌───────────────────────────────────────────────────────┐
 HTTP ──▶ │ adapters/inbound/http      (FastAPI : routes, DTO)    │
          └───────────────┬───────────────────────────────────────┘
                          ▼ appelle
          ┌───────────────────────────────────────────────────────┐
          │ application/                                          │
          │   use_cases/   CreateOrder, CancelOrder, ValidateOrder│
          │   ports.py     ProductRepository, OrderRepository,    │
          │                UnitOfWork  (interfaces)               │
          └───────────────┬───────────────────────────────────────┘
                          ▼ utilise
          ┌───────────────────────────────────────────────────────┐
          │ domain/   Product, Order, Money, Quantity, services   │
          │           ← Python pur, aucune dépendance             │
          └───────────────────────────────────────────────────────┘
                          ▲ implémente les ports
          ┌───────────────┴───────────────────────────────────────┐
          │ adapters/outbound/persistence  (SQLAlchemy/PostgreSQL)│
          └───────────────────────────────────────────────────────┘
```

**Règle de dépendance : tout pointe vers le domaine.** `domain/` n'importe rien d'externe, `application/`
n'importe que `domain/`. Les adaptateurs (HTTP, PostgreSQL) dépendent de l'application, jamais l'inverse.
`app/main.py` est la *racine de composition* : le seul fichier qui connaît toutes les couches et les assemble.

```
app/
  domain/                    LE MÉTIER
    value_objects.py         Money (Decimal, centimes), Quantity (entier > 0)
    product.py               Agrégat Product : reserve(), restock(), stock jamais négatif
    order.py                 Agrégat Order : validate(), cancel(), statuts, total
    services.py              place_order(), cancel_order() : règles multi-agrégats
    errors.py                Erreurs métier (sans notion de HTTP)
  application/
    ports.py                 Interfaces attendues de l'extérieur (repositories, Unit of Work)
    use_cases/               Un fichier par cas d'usage (+ queries.py pour la lecture)
  adapters/
    inbound/http/            Routes FastAPI, DTO Pydantic, traduction erreurs -> codes HTTP
    outbound/persistence/    Tables ORM, repositories, Unit of Work PostgreSQL
  config.py                  Lecture du .env, construction de l'URL de connexion
  main.py                    Racine de composition
db/
  script.sql                 Schéma + données
```

### Concepts DDD utilisés

| Concept | Où | Rôle |
|---|---|---|
| **Objet-valeur** | `Money`, `Quantity` | Immuables, valident leurs invariants à la construction : une `Quantity` de 0 ne peut pas exister |
| **Agrégat / racine** | `Order` (avec ses `OrderLine`), `Product` | Unité de cohérence ; seule la racine modifie son état |
| **Service de domaine** | `place_order`, `cancel_order` | Règle qui touche plusieurs agrégats (commande + produits) |
| **Repository** | `ProductRepository`, `OrderRepository` | Collection d'agrégats ; le domaine ignore SQL |
| **Unit of Work** | `UnitOfWork` | Une transaction : tout est validé ensemble ou rien |
| **Erreurs métier** | `domain/errors.py` | Langage du domaine (`InsufficientStock`…), traduites en HTTP par l'adaptateur |

## API

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/products` | Liste des produits |
| POST | `/api/orders` | Crée une commande `{"items":[{"product_id":1,"quantity":2}]}` → 201 |
| GET | `/api/orders` | Liste des commandes (`?status=PENDING\|VALIDATED\|CANCELLED`) |
| GET | `/api/orders/{id}` | Détail d'une commande |
| POST | `/api/orders/{id}/validate` | En attente → Validée |
| POST | `/api/orders/{id}/cancel` | Annule et restitue le stock |

Erreurs : `{"error": {"code", "message", "details"}}`

| Situation | HTTP | `error.code` |
|---|---|---|
| Quantité ≤ 0 | 422 | `invalid_quantity` |
| Commande sans ligne | 422 | `empty_order` |
| Produit / commande inexistant(e) | 404 | `product_not_found` / `order_not_found` |
| Stock insuffisant | 409 | `insufficient_stock` (demandé vs disponible par produit) |
| Commande déjà annulée | 409 | `order_already_cancelled` |
| Validation d'une commande non « en attente » | 409 | `invalid_status_transition` |
| JSON mal formé (type erroné, champ manquant) | 422 | format Pydantic standard (`detail`) |

## Choix techniques et hypothèses

**Cycle de vie des statuts.** L'énoncé demande de mettre à jour le stock « après validation de la commande » et de
le restituer à l'annulation. Interprétation retenue :
- à la création, les vérifications sont faites puis la commande est enregistrée **En attente** et le **stock est
  immédiatement réservé** (sinon deux clients pourraient commander le dernier article) ;
- `validate` : **En attente → Validée** (le stock est déjà réservé) ;
- `cancel` : possible depuis **En attente** ou **Validée**, restitue le stock ; refusé si déjà **Annulée**.

Si la règle voulue était « le stock ne baisse qu'à la validation », il suffirait de déplacer la réservation de
`place_order` vers un service de validation (en revérifiant le stock à ce moment-là).

**Où vit chaque règle.** Les règles métier sont dans le domaine, pas dans les routes ni en base : `Quantity`
refuse 0 et les négatifs, `Product` refuse un stock négatif, `Order.cancel()` refuse une seconde annulation.
Pydantic ne valide que la *forme* du JSON. Résultat : les mêmes règles s'appliquent quel que soit le point d'entrée
(HTTP, CLI, file de messages…) et se testent sans base ni serveur.

**Atomicité.** Chaque cas d'usage ouvre une transaction (Unit of Work). Les services de domaine vérifient *tout*
avant de modifier quoi que ce soit ; en cas d'erreur, la transaction est annulée : aucune commande, aucun stock modifié.

**Concurrence.** Les produits (et la commande, pour l'annulation) sont verrouillés avec `SELECT ... FOR UPDATE`,
toujours dans l'ordre croissant des ids (pas de deadlock). Deux commandes simultanées sur le dernier article :
l'une passe, l'autre reçoit 409 ; deux annulations simultanées ne restituent le stock qu'une fois (testé avec
des threads sur PostgreSQL réel).

**Lignes en double.** Un produit présent sur plusieurs lignes est cumulé avant la vérification du stock, puis fusionné.

**Défense en profondeur.** Contraintes `CHECK` dans `script.sql` (`stock >= 0`, `quantity > 0`, statuts valides) :
même un bug applicatif ne pourrait pas corrompre les données (testé).

**Argent.** `NUMERIC` en base, `Decimal` en Python via `Money` (arrondi au centime), jamais de `float`.
L'API renvoie les montants en chaînes (`"204.30"`) pour ne perdre aucune précision côté client.

**Historique figé.** Nom et prix du produit sont copiés dans chaque ligne de commande.

**Schéma en SQL plutôt qu'ORM.** `script.sql` est la source de vérité du schéma ; les classes SQLAlchemy ne servent
qu'à lire/écrire. Les tests d'intégration rejouent ce script, donc il est lui-même vérifié.

**Pas de migrations.** Suffisant pour une v1 ; en production j'ajouterais Alembic.

**Secrets.** Identifiants dans `.env` (ignoré par git), modèle fourni dans `.env.example`. L'URL de connexion est
construite par `sqlalchemy.engine.URL.create`, qui échappe les caractères spéciaux du mot de passe. L'application
refuse de démarrer avec un message explicite si une variable obligatoire manque.

## Pistes d'amélioration

- Migrations Alembic, authentification, pagination de `/api/orders`
- CRUD produits (hors périmètre de l'énoncé)
- Clé d'idempotence sur `POST /api/orders` (double clic, retry réseau)
- Événements de domaine (`OrderPlaced`, `OrderCancelled`) si d'autres traitements doivent réagir
- CI (GitHub Actions) avec un service PostgreSQL
