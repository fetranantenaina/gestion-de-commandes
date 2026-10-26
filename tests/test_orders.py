from decimal import Decimal

from tests.conftest import CAHIER, CLE_USB, STYLO


def order_payload(*lines):
    return {"items": [{"product_id": pid, "quantity": qty} for pid, qty in lines]}


# ---------- Cas 1 : commande valide avec plusieurs produits ----------
def test_valid_order_with_several_products(client, stock_of):
    r = client.post("/api/orders", json=order_payload((STYLO, 2), (CAHIER, 1)))

    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "PENDING"
    assert Decimal(body["total_amount"]) == Decimal("9.00")  # 2*2.50 + 1*4.00
    assert len(body["items"]) == 2
    assert body["created_at"]
    assert stock_of(STYLO) == 98
    assert stock_of(CAHIER) == 49


# ---------- Cas 2 : quantité supérieure au stock ----------
def test_quantity_above_stock_is_rejected(client, stock_of):
    r = client.post("/api/orders", json=order_payload((CLE_USB, 4)))

    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "insufficient_stock"
    assert err["details"][0] == {
        "product_id": CLE_USB,
        "product_name": "Clé USB",
        "requested": 4,
        "available": 3,
    }
    assert stock_of(CLE_USB) == 3
    assert client.get("/api/orders").json() == []


def test_exact_stock_is_accepted(client, stock_of):
    r = client.post("/api/orders", json=order_payload((CLE_USB, 3)))
    assert r.status_code == 201
    assert stock_of(CLE_USB) == 0


# ---------- Cas 3 : quantité nulle ou négative ----------
def test_zero_or_negative_quantity_is_rejected(client, stock_of):
    for qty in (0, -1):
        r = client.post("/api/orders", json=order_payload((STYLO, qty)))
        assert r.status_code == 422
    assert stock_of(STYLO) == 100
    assert client.get("/api/orders").json() == []


def test_empty_order_is_rejected(client):
    assert client.post("/api/orders", json={"items": []}).status_code == 422


# ---------- Cas 4 : produit inexistant ----------
def test_unknown_product_is_rejected(client, stock_of):
    r = client.post("/api/orders", json=order_payload((STYLO, 1), (999, 1)))

    assert r.status_code == 404
    assert r.json()["error"]["code"] == "product_not_found"
    assert stock_of(STYLO) == 100  # le produit valide n'a pas été touché
    assert client.get("/api/orders").json() == []


# ---------- Atomicité : une ligne invalide annule tout ----------
def test_failure_on_one_line_leaves_all_stocks_untouched(client, stock_of):
    r = client.post("/api/orders", json=order_payload((STYLO, 5), (CLE_USB, 10)))

    assert r.status_code == 409
    assert stock_of(STYLO) == 100
    assert stock_of(CLE_USB) == 3
    assert client.get("/api/orders").json() == []


# ---------- Le même produit sur plusieurs lignes est cumulé ----------
def test_duplicate_lines_are_summed_for_stock_check(client, stock_of):
    # 2 + 2 = 4 > 3 : doit échouer même si chaque ligne prise seule passerait
    r = client.post("/api/orders", json=order_payload((CLE_USB, 2), (CLE_USB, 2)))
    assert r.status_code == 409
    assert stock_of(CLE_USB) == 3


def test_duplicate_lines_are_merged_into_one(client, stock_of):
    r = client.post("/api/orders", json=order_payload((STYLO, 1), (STYLO, 2)))
    assert r.status_code == 201
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["quantity"] == 3
    assert stock_of(STYLO) == 97


# ---------- Cas 5 : annulation et restitution du stock ----------
def test_cancel_restores_stock(client, stock_of):
    created = client.post("/api/orders", json=order_payload((STYLO, 2), (CAHIER, 5))).json()
    assert stock_of(STYLO) == 98 and stock_of(CAHIER) == 45

    r = client.post(f"/api/orders/{created['id']}/cancel")

    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"
    assert stock_of(STYLO) == 100
    assert stock_of(CAHIER) == 50


def test_cancel_validated_order_restores_stock(client, stock_of):
    created = client.post("/api/orders", json=order_payload((STYLO, 2))).json()
    client.post(f"/api/orders/{created['id']}/validate")

    r = client.post(f"/api/orders/{created['id']}/cancel")

    assert r.status_code == 200
    assert stock_of(STYLO) == 100


# ---------- Cas 6 : double annulation ----------
def test_cannot_cancel_twice(client, stock_of):
    created = client.post("/api/orders", json=order_payload((STYLO, 2))).json()
    assert client.post(f"/api/orders/{created['id']}/cancel").status_code == 200

    r = client.post(f"/api/orders/{created['id']}/cancel")

    assert r.status_code == 409
    assert r.json()["error"]["code"] == "order_already_cancelled"
    assert stock_of(STYLO) == 100  # pas de double restitution (pas 102)


def test_cancel_unknown_order(client):
    assert client.post("/api/orders/999/cancel").status_code == 404


# ---------- Statuts ----------
def test_validate_order(client):
    created = client.post("/api/orders", json=order_payload((STYLO, 1))).json()
    r = client.post(f"/api/orders/{created['id']}/validate")
    assert r.status_code == 200 and r.json()["status"] == "VALIDATED"


def test_cannot_validate_cancelled_or_validated_order(client):
    a = client.post("/api/orders", json=order_payload((STYLO, 1))).json()
    client.post(f"/api/orders/{a['id']}/cancel")
    assert client.post(f"/api/orders/{a['id']}/validate").status_code == 409

    b = client.post("/api/orders", json=order_payload((STYLO, 1))).json()
    client.post(f"/api/orders/{b['id']}/validate")
    assert client.post(f"/api/orders/{b['id']}/validate").status_code == 409


# ---------- Consultation ----------
def test_list_orders_exposes_required_fields(client):
    client.post("/api/orders", json=order_payload((STYLO, 1)))
    orders = client.get("/api/orders").json()

    assert len(orders) == 1
    assert {"id", "created_at", "total_amount", "status"} <= orders[0].keys()


def test_price_is_snapshotted_in_order(client):
    from tests.conftest import TestingSession
    from app.models import Product

    created = client.post("/api/orders", json=order_payload((STYLO, 2))).json()
    with TestingSession() as db:
        db.get(Product, STYLO).unit_price = Decimal("99.00")
        db.commit()

    again = client.get(f"/api/orders/{created['id']}").json()
    assert Decimal(again["total_amount"]) == Decimal("5.00")
    assert Decimal(again["items"][0]["unit_price"]) == Decimal("2.50")
