import app as app_module
from openfoodfacts_client import OpenFoodFactsError


def add_item(client, **overrides):
    payload = {"name": "Oat Milk", "price": 4.99, "stock": 10}
    payload.update(overrides)
    return client.post("/inventory", json=payload)


def test_get_inventory_starts_empty(client):
    response = client.get("/inventory")

    assert response.status_code == 200
    assert response.get_json() == []


def test_post_creates_item(client):
    response = add_item(client)
    data = response.get_json()

    assert response.status_code == 201
    assert data["id"] == 1
    assert data["name"] == "Oat Milk"
    assert data["stock"] == 10
    assert data["brand"] is None


def test_post_assigns_incrementing_ids(client):
    add_item(client)
    second = add_item(client, name="Rice")

    assert second.get_json()["id"] == 2


def test_post_rejects_missing_name(client):
    response = client.post("/inventory", json={"price": 1, "stock": 1})

    assert response.status_code == 400
    assert "name" in response.get_json()["error"]


def test_post_rejects_negative_price(client):
    response = add_item(client, price=-1)

    assert response.status_code == 400


def test_post_rejects_non_integer_stock(client):
    response = add_item(client, stock=2.5)

    assert response.status_code == 400


def test_get_single_item(client):
    add_item(client)

    response = client.get("/inventory/1")

    assert response.status_code == 200
    assert response.get_json()["name"] == "Oat Milk"


def test_get_missing_item_returns_404(client):
    response = client.get("/inventory/99")

    assert response.status_code == 404


def test_patch_updates_price_and_stock(client):
    add_item(client)

    response = client.patch("/inventory/1", json={"price": 5.5, "stock": 3})
    data = response.get_json()

    assert response.status_code == 200
    assert data["price"] == 5.5
    assert data["stock"] == 3
    assert data["name"] == "Oat Milk"


def test_patch_missing_item_returns_404(client):
    response = client.patch("/inventory/99", json={"price": 1})

    assert response.status_code == 404


def test_patch_rejects_invalid_value(client):
    add_item(client)

    response = client.patch("/inventory/1", json={"price": "free"})

    assert response.status_code == 400


def test_patch_rejects_empty_body(client):
    add_item(client)

    response = client.patch("/inventory/1", json={})

    assert response.status_code == 400


def test_delete_removes_item(client):
    add_item(client)

    response = client.delete("/inventory/1")

    assert response.status_code == 204
    assert client.get("/inventory/1").status_code == 404


def test_delete_missing_item_returns_404(client):
    response = client.delete("/inventory/99")

    assert response.status_code == 404


def test_lookup_requires_barcode_or_name(client):
    response = client.get("/lookup")

    assert response.status_code == 400


def test_lookup_by_barcode_returns_product(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "lookup_by_barcode",
        lambda barcode: {"barcode": barcode, "name": "Spring Water"},
    )

    response = client.get("/lookup?barcode=3274080005003")

    assert response.status_code == 200
    assert response.get_json()["name"] == "Spring Water"


def test_lookup_unknown_barcode_returns_404(client, monkeypatch):
    monkeypatch.setattr(app_module, "lookup_by_barcode", lambda barcode: None)

    response = client.get("/lookup?barcode=0000000000000")

    assert response.status_code == 404


def test_lookup_by_name_returns_list(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "search_by_name",
        lambda name: [{"barcode": "111", "name": "Oat Milk"}],
    )

    response = client.get("/lookup?name=oat")

    assert response.status_code == 200
    assert response.get_json()[0]["name"] == "Oat Milk"


def test_lookup_returns_502_when_external_api_fails(client, monkeypatch):
    def failing_lookup(barcode):
        raise OpenFoodFactsError("OpenFoodFacts request failed")

    monkeypatch.setattr(app_module, "lookup_by_barcode", failing_lookup)

    response = client.get("/lookup?barcode=3274080005003")

    assert response.status_code == 502
    assert "error" in response.get_json()


def test_enrich_adds_api_details_without_overwriting_name(client, monkeypatch):
    add_item(client, barcode="3274080005003")
    monkeypatch.setattr(
        app_module,
        "lookup_by_barcode",
        lambda barcode: {
            "barcode": barcode,
            "name": "Spring Water",
            "brand": "Cristaline",
            "image_url": "https://example.com/water.jpg",
            "nutriscore": "a",
            "quantity": "1.5 L",
        },
    )

    response = client.post("/inventory/1/enrich")
    data = response.get_json()

    assert response.status_code == 200
    assert data["brand"] == "Cristaline"
    assert data["nutriscore"] == "a"
    assert data["name"] == "Oat Milk"


def test_enrich_requires_barcode(client):
    add_item(client)

    response = client.post("/inventory/1/enrich")

    assert response.status_code == 400