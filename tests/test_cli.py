import requests

import cli


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data

    def json(self):
        if self._data is None:
            raise ValueError("no JSON body")
        return self._data


def patch_requests(monkeypatch, response):
    """Replace requests.request with a stand-in that records calls."""
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        return response

    monkeypatch.setattr(cli.requests, "request", fake_request)
    return calls


def test_list_prints_items(monkeypatch, capsys):
    patch_requests(
        monkeypatch,
        FakeResponse(200, [{"id": 1, "name": "Oat Milk", "price": 4.99, "stock": 10}]),
    )

    exit_code = cli.main(["list"])

    assert exit_code == 0
    assert "[1] Oat Milk - $4.99 - stock: 10" in capsys.readouterr().out


def test_list_reports_empty_inventory(monkeypatch, capsys):
    patch_requests(monkeypatch, FakeResponse(200, []))

    cli.main(["list"])

    assert "Inventory is empty." in capsys.readouterr().out


def test_add_sends_expected_payload(monkeypatch, capsys):
    calls = patch_requests(
        monkeypatch,
        FakeResponse(201, {"id": 1, "name": "Oat Milk", "price": 4.99, "stock": 10}),
    )

    exit_code = cli.main(
        ["add", "--name", "Oat Milk", "--price", "4.99", "--stock", "10"]
    )

    assert exit_code == 0
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/inventory")
    assert calls[0]["json"] == {"name": "Oat Milk", "price": 4.99, "stock": 10}
    assert "Added:" in capsys.readouterr().out


def test_update_sends_only_provided_fields(monkeypatch):
    calls = patch_requests(
        monkeypatch,
        FakeResponse(200, {"id": 1, "name": "Oat Milk", "price": 5.5, "stock": 10}),
    )

    cli.main(["update", "1", "--price", "5.5"])

    assert calls[0]["method"] == "PATCH"
    assert calls[0]["url"].endswith("/inventory/1")
    assert calls[0]["json"] == {"price": 5.5}


def test_update_without_fields_fails(monkeypatch, capsys):
    patch_requests(monkeypatch, FakeResponse(200, {}))

    exit_code = cli.main(["update", "1"])

    assert exit_code == 1
    assert "at least one" in capsys.readouterr().err


def test_delete_prints_confirmation(monkeypatch, capsys):
    calls = patch_requests(monkeypatch, FakeResponse(204))

    exit_code = cli.main(["delete", "3"])

    assert exit_code == 0
    assert calls[0]["method"] == "DELETE"
    assert "Deleted item 3." in capsys.readouterr().out


def test_view_prints_api_error_message(monkeypatch, capsys):
    patch_requests(monkeypatch, FakeResponse(404, {"error": "Item not found"}))

    exit_code = cli.main(["view", "99"])

    assert exit_code == 1
    assert "Item not found" in capsys.readouterr().err


def test_find_by_barcode_prints_product(monkeypatch, capsys):
    calls = patch_requests(
        monkeypatch,
        FakeResponse(
            200, {"barcode": "3274080005003", "name": "Spring Water", "brand": "Cristaline"}
        ),
    )

    exit_code = cli.main(["find", "--barcode", "3274080005003"])

    assert exit_code == 0
    assert calls[0]["params"] == {"barcode": "3274080005003"}
    assert "Spring Water" in capsys.readouterr().out


def test_find_by_name_prints_each_result(monkeypatch, capsys):
    patch_requests(
        monkeypatch,
        FakeResponse(
            200,
            [
                {"barcode": "111", "name": "Oat Milk", "brand": "Oatly"},
                {"barcode": "222", "name": "Oat Drink", "brand": "Alpro"},
            ],
        ),
    )

    cli.main(["find", "--name", "oat"])
    output = capsys.readouterr().out

    assert "Oat Milk" in output
    assert "Oat Drink" in output


def test_unreachable_api_returns_friendly_error(monkeypatch, capsys):
    def raise_connection_error(method, url, **kwargs):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(cli.requests, "request", raise_connection_error)

    exit_code = cli.main(["list"])

    assert exit_code == 1
    assert "could not reach" in capsys.readouterr().err