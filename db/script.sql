-- =====================================================================
-- script.sql : schéma + jeu de données initial (PostgreSQL)
--
-- Idempotent : peut être rejoué sans erreur ni doublon.
--   * Docker : exécuté automatiquement au premier démarrage du conteneur db
--   * Manuel : psql -h localhost -p 5433 -U orders -d orders -f db/script.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Schéma
--    Les contraintes CHECK sont le dernier garde-fou de cohérence : même un bug
--    applicatif ne peut pas produire un stock négatif ou une quantité nulle.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(200)  NOT NULL,
    unit_price  NUMERIC(10,2) NOT NULL,
    stock       INTEGER       NOT NULL,
    CONSTRAINT ck_products_price_non_negative CHECK (unit_price >= 0),
    CONSTRAINT ck_products_stock_non_negative CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT now(),
    total_amount  NUMERIC(12,2) NOT NULL,
    status        VARCHAR(20)   NOT NULL,
    CONSTRAINT ck_orders_total_non_negative CHECK (total_amount >= 0),
    CONSTRAINT ck_orders_status_valid CHECK (status IN ('PENDING', 'VALIDATED', 'CANCELLED'))
);

-- Le nom et le prix du produit sont copiés dans la ligne : l'historique ne change
-- pas si le produit est modifié plus tard.
CREATE TABLE IF NOT EXISTS order_items (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id      INTEGER       NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id    INTEGER       NOT NULL REFERENCES products (id),
    product_name  VARCHAR(200)  NOT NULL,
    quantity      INTEGER       NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL,
    CONSTRAINT ck_order_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT uq_order_items_order_product UNIQUE (order_id, product_id)
);

CREATE INDEX IF NOT EXISTS ix_orders_created_at ON orders (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items (order_id);

-- ---------------------------------------------------------------------
-- 2. Jeu de données initial (inséré uniquement si la table est vide)
--    - Clé USB 64 Go : stock de 3  -> tester « stock insuffisant »
--    - Tapis de souris : stock de 0 -> rupture de stock
-- ---------------------------------------------------------------------
INSERT INTO products (name, unit_price, stock)
SELECT v.name, v.unit_price, v.stock
FROM (VALUES
    ('Clavier mécanique', 89.90,  25),
    ('Souris sans fil',   24.50,  40),
    ('Écran 24 pouces',  149.00,  10),
    ('Câble HDMI 2 m',     7.90, 100),
    ('Clé USB 64 Go',     12.90,   3),
    ('Webcam HD',         39.99,  15),
    ('Casque audio',      59.00,   8),
    ('Tapis de souris',    9.90,   0)
) AS v (name, unit_price, stock)
WHERE NOT EXISTS (SELECT 1 FROM products);
