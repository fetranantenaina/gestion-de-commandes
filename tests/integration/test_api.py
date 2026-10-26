"""Tests d'API de bout en bout (HTTP -> cas d'usage -> domaine -> PostgreSQL réel)."""
from decimal import Decimal

from tests.integration.conftest import CLAVIER, CLE_USB, ECRAN, SOURIS, TAPIS


def order(*lines):
    return {"items": [{"product_id": pid, "quantity": qty} for pid, qty in lines]}


def test_script_sql_is_idempotent(engine, client):
    from tests.integration.conftest import SCRIPT_SQL

    with engine.begin() as conn:
        conn.exec_driver_sql(SCRIPT_SQL.read_text(encoding="utf-8"))  # 2e exécution
    assert len(client.get("/api/products").json()) == 8


# ---------- Cas 1 : commande valide avec plusieurs produits ----------
def test_valid_order_with_several_products(client, stock_of):
    r = client.post("/api/orders", json=order((CLAVIER, 2), (SOURIS, 1)))

    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "PENDING"
    assert Decimal(body["total_amount"]) == Decimal("204.30")  # 2*89.90 + 24.50
    assert len(body["items"]) == 2 and body["created_at"]
    assert stock_of(CLAVIER) == 23 and stock_of(SOURIS) == 39


# ---------- Cas 2 : quantité supérieure au stock ----------
def test_quantity_above_stock_is_rejected(client, stock_of):
    r = client.post("/api/orders", json=order((CLE_USB, 4)))

    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "insufficient_stock"
    assert err["details"] == [
        {"product_id": CLE_USB, "product_name": "Clé USB 64 Go", "requested": 4, "available": 3}
    ]
    assert stock_of(CLE_USB) == 3
    assert client.get("/api/orders").json() == []


def test_exact_stock_is_accepted_and_out_of_stock_rejected(client, stock_of):
    assert client.post("/api/orders", json=order((CLE_USB, 3))).status_code == 201
    assert stock_of(CLE_USB) == 0
    assert client.post("/api/orders", json=order((TAPIS, 1))).status_code == 409  # rupture


# ---------- Cas 3 : quantité nulle ou négative ----------
def test_zero_or_negative_quantity_is_rejected(client, stock_of):
    for qty in (0, -1):
        r = client.post("/api/orders", json=order((CLAVIER, qty)))
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "invalid_quantity"
    assert stock_of(CLAVIER) == 25
    assert client.get("/api/orders").json() == []


def test_empty_order_is_rejected(client):
    r = client.post("/api/orders", json={"items": []})
    assert r.status_code == 422 and r.json()["error"]["code"] == "empty_order"


def test_malformed_payload_is_rejected(client):
    assert client.post("/api/orders", json={"items": [{"product_id": "x"}]}).status_code == 422


# ---------- Cas 4 : produit inexistant ----------
def test_unknown_product_is_rejected(client, stock_of):
    r = client.post("/api/orders", json=order((CLAVIER, 1), (999, 1)))

    assert r.status_code == 404
    assert r.json()["error"]["code"] == "product_not_found"
    assert stock_of(CLAVIER) == 25
    assert client.get("/api/orders").json() == []


# ---------- Atomicité ----------
def test_failure_on_one_line_leaves_all_stocks_untouched(client, stock_of):
    r = client.post("/api/orders", json=order((CLAVIER, 5), (CLE_USB, 10)))
    assert r.status_code == 409
    assert stock_of(CLAVIER) == 25 and stock_of(CLE_USB) == 3
    assert client.get("/api/orders").json() == []


def test_duplicate_lines_are_summed_then_merged(client, stock_of):
    assert client.post("/api/orders", json=order((CLE_USB, 2), (CLE_USB, 2))).status_code == 409
    assert stock_of(CLE_USB) == 3

    r = client.post("/api/orders", json=order((CLAVIER, 1), (CLAVIER, 2)))
    assert r.status_code == 201
    assert [i["quantity"] for i in r.json()["items"]] == [3]
    assert stock_of(CLAVIER) == 22


# ---------- Cas 5 : annulation + restitution du stock ----------
def test_cancel_restores_stock(client, stock_of):
    created = client.post("/api/orders", json=order((CLAVIER, 2), (ECRAN, 5))).json()
    assert stock_of(CLAVIER) == 23 and stock_of(ECRAN) == 5

    r = client.post(f"/api/orders/{created['id']}/cancel")

    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert stock_of(CLAVIER) == 25 and stock_of(ECRAN) == 10


def test_cancel_validated_order_restores_stock(client, stock_of):
    created = client.post("/api/orders", json=order((CLAVIER, 2))).json()
    client.post(f"/api/orders/{created['id']}/validate")
    assert client.post(f"/api/orders/{created['id']}/cancel").status_code == 200
    assert stock_of(CLAVIER) == 25


# ---------- Cas 6 : double annulation ----------
def test_cannot_cancel_twice(client, stock_of):
    created = client.post("/api/orders", json=order((CLAVIER, 2))).json()
    assert client.post(f"/api/orders/{created['id']}/cancel").status_code == 200

    r = client.post(f"/api/orders/{created['id']}/cancel")

    assert r.status_code == 409
    assert r.json()["error"]["code"] == "order_already_cancelled"
    assert stock_of(CLAVIER) == 25  # pas 27 : stock restitué une seule fois


def test_unknown_order_returns_404(client):
    assert client.post("/api/orders/999/cancel").status_code == 404
    assert client.post("/api/orders/999/validate").status_code == 404
    assert client.get("/api/orders/999").status_code == 404


# ---------- Statuts & consultation ----------
def test_validate_and_invalid_transitions(client):
    a = client.post("/api/orders", json=order((CLAVIER, 1))).json()
    assert client.post(f"/api/orders/{a['id']}/validate").json()["status"] == "VALIDATED"
    assert client.post(f"/api/orders/{a['id']}/validate").status_code == 409

    b = client.post("/api/orders", json=order((CLAVIER, 1))).json()
    client.post(f"/api/orders/{b['id']}/cancel")
    assert client.post(f"/api/orders/{b['id']}/validate").status_code == 409


def test_list_orders_exposes_required_fields_and_filters(client):
    a = client.post("/api/orders", json=order((CLAVIER, 1))).json()
    client.post("/api/orders", json=order((SOURIS, 1)))
    client.post(f"/api/orders/{a['id']}/cancel")

    orders = client.get("/api/orders").json()
    assert len(orders) == 2 and {"id", "created_at", "total_amount", "status"} <= orders[0].keys()
    assert [o["id"] for o in orders] == sorted((o["id"] for o in orders), reverse=True)
    assert len(client.get("/api/orders?status=CANCELLED").json()) == 1


def test_order_keeps_price_snapshot_after_product_update(client, sql):
    created = client.post("/api/orders", json=order((CLAVIER, 2))).json()
    sql(f"UPDATE products SET unit_price = 999 WHERE id = {CLAVIER}")

    again = client.get(f"/api/orders/{created['id']}").json()
    assert Decimal(again["total_amount"]) == Decimal("179.80")
    assert Decimal(again["items"][0]["unit_price"]) == Decimal("89.90")


# ---------- Défense en profondeur : contraintes SQL ----------
def test_database_refuses_negative_stock(sql):
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        sql(f"UPDATE products SET stock = -1 WHERE id = {CLAVIER}")
