import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["FRONTEND_DIR"] = "/nonexistent"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def menu(client):
    return client.get("/api/menu").json()


def find_product(menu, name):
    return next(p for c in menu for p in c["products"] if p["name"] == name)


def test_menu_shape(menu):
    assert len(menu) == 12
    clasica = find_product(menu, "Hamburguesa clásica")
    assert [g["title"] for g in clasica["option_groups"]] == ["Salsas", "Bebida"]
    assert find_product(menu, "Cerveza Corona")["option_groups"] == []


def test_create_order_computes_price_on_server(client, menu):
    clasica = find_product(menu, "Hamburguesa clásica")
    salsas, bebidas = clasica["option_groups"]
    bbq = next(o for o in salsas["options"] if o["name"] == "BBQ")
    coca = next(o for o in bebidas["options"] if o["name"] == "Coca Cola 400ml")

    res = client.post("/api/orders", json={
        "lines": [{"product_id": clasica["id"], "qty": 2, "option_ids": [bbq["id"], coca["id"]]}]
    })
    assert res.status_code == 201
    body = res.json()
    assert body["lines"][0]["unit_price"] == 16900 + 1000 + 4000
    assert body["lines"][0]["options"] == ["BBQ", "Coca Cola 400ml"]
    assert body["total"] == 2 * 21900
    assert body["created_at"].endswith("Z") or body["created_at"].endswith("+00:00")


def test_free_product(client):
    res = client.post("/api/orders", json={"lines": [{"name": "Adicional", "unit_price": 5000}]})
    assert res.status_code == 201
    assert res.json()["total"] == 5000


def test_rejects_too_many_options(client, menu):
    clasica = find_product(menu, "Hamburguesa clásica")
    bebidas = clasica["option_groups"][1]
    ids = [o["id"] for o in bebidas["options"][:2]]
    res = client.post("/api/orders", json={"lines": [{"product_id": clasica["id"], "option_ids": ids}]})
    assert res.status_code == 422


def test_rejects_foreign_option(client, menu):
    corona = find_product(menu, "Cerveza Corona")
    bebidas = find_product(menu, "Hamburguesa clásica")["option_groups"][1]
    res = client.post("/api/orders", json={
        "lines": [{"product_id": corona["id"], "option_ids": [bebidas["options"][0]["id"]]}]
    })
    assert res.status_code == 422


def test_rejects_empty_order_and_unknown_product(client):
    assert client.post("/api/orders", json={"lines": []}).status_code == 422
    assert client.post("/api/orders", json={"lines": [{"product_id": 9999}]}).status_code == 422


def test_replace_filter_and_delete(client, menu):
    corona = find_product(menu, "Cerveza Corona")
    created = client.post("/api/orders", json={"lines": [{"product_id": corona["id"]}]}).json()
    oid = created["id"]

    res = client.put(f"/api/orders/{oid}", json={
        "paid": True, "lines": [{"product_id": corona["id"], "qty": 3}]
    })
    assert res.status_code == 200
    assert res.json()["paid"] is True
    assert res.json()["total"] == 27000
    assert len(res.json()["lines"]) == 1

    paid_ids = [o["id"] for o in client.get("/api/orders?paid=true").json()]
    pending_ids = [o["id"] for o in client.get("/api/orders?paid=false").json()]
    assert oid in paid_ids and oid not in pending_ids

    assert client.delete(f"/api/orders/{oid}").status_code == 204
    assert client.get(f"/api/orders/{oid}").status_code == 404
    assert client.put(f"/api/orders/{oid}", json={"lines": [{"product_id": corona["id"]}]}).status_code == 404
